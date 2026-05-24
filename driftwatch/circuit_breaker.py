"""Simple per-target circuit breaker to stop hammering failing remotes."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class BreakerState(Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # failing; requests blocked
    HALF_OPEN = "half_open"  # probe allowed


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3      # consecutive failures before opening
    recovery_timeout: float = 60.0  # seconds before moving to HALF_OPEN
    success_threshold: int = 1      # successes in HALF_OPEN to close again

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")


@dataclass
class _BreakerEntry:
    state: BreakerState = BreakerState.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    opened_at: float = 0.0


class CircuitBreaker:
    """Tracks per-target circuit state."""

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._cfg = config or CircuitBreakerConfig()
        self._entries: Dict[str, _BreakerEntry] = {}

    def _entry(self, target: str) -> _BreakerEntry:
        if target not in self._entries:
            self._entries[target] = _BreakerEntry()
        return self._entries[target]

    def is_allowed(self, target: str) -> bool:
        """Return True if a request to *target* should be attempted."""
        e = self._entry(target)
        if e.state == BreakerState.CLOSED:
            return True
        if e.state == BreakerState.OPEN:
            if time.monotonic() - e.opened_at >= self._cfg.recovery_timeout:
                e.state = BreakerState.HALF_OPEN
                e.consecutive_successes = 0
                return True
            return False
        # HALF_OPEN — allow one probe
        return True

    def record_success(self, target: str) -> None:
        e = self._entry(target)
        e.consecutive_failures = 0
        if e.state == BreakerState.HALF_OPEN:
            e.consecutive_successes += 1
            if e.consecutive_successes >= self._cfg.success_threshold:
                e.state = BreakerState.CLOSED
        # already CLOSED — nothing to do

    def record_failure(self, target: str) -> None:
        e = self._entry(target)
        e.consecutive_successes = 0
        e.consecutive_failures += 1
        if e.state in (BreakerState.CLOSED, BreakerState.HALF_OPEN):
            if e.consecutive_failures >= self._cfg.failure_threshold:
                e.state = BreakerState.OPEN
                e.opened_at = time.monotonic()

    def state(self, target: str) -> BreakerState:
        return self._entry(target).state

    def reset(self, target: str) -> None:
        self._entries.pop(target, None)
