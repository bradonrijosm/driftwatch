"""Watchdog: tracks consecutive failures per target and marks targets as
'unhealthy' after a configurable threshold."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from driftwatch.checker import DriftResult


@dataclass
class WatchdogConfig:
    failure_threshold: int = 3
    recovery_threshold: int = 1

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_threshold < 1:
            raise ValueError("recovery_threshold must be >= 1")


@dataclass
class _TargetHealth:
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    healthy: bool = True


@dataclass
class Watchdog:
    """Maintains per-target health state based on DriftResult outcomes."""

    config: WatchdogConfig = field(default_factory=WatchdogConfig)
    _state: Dict[str, _TargetHealth] = field(default_factory=dict, repr=False)

    def _get(self, target_name: str) -> _TargetHealth:
        if target_name not in self._state:
            self._state[target_name] = _TargetHealth()
        return self._state[target_name]

    def record(self, result: DriftResult) -> None:
        """Update health state for the target described by *result*."""
        name = result.target.name
        entry = self._get(name)
        is_ok = result.status == "ok"

        if is_ok:
            entry.consecutive_failures = 0
            entry.consecutive_successes += 1
            if not entry.healthy and entry.consecutive_successes >= self.config.recovery_threshold:
                entry.healthy = True
        else:
            entry.consecutive_successes = 0
            entry.consecutive_failures += 1
            if entry.healthy and entry.consecutive_failures >= self.config.failure_threshold:
                entry.healthy = False

    def is_healthy(self, target_name: str) -> bool:
        """Return True if the target is currently considered healthy."""
        return self._get(target_name).healthy

    def consecutive_failures(self, target_name: str) -> int:
        return self._get(target_name).consecutive_failures

    def consecutive_successes(self, target_name: str) -> int:
        return self._get(target_name).consecutive_successes

    def unhealthy_targets(self) -> list[str]:
        """Return names of all currently unhealthy targets."""
        return [name for name, h in self._state.items() if not h.healthy]

    def reset(self, target_name: str) -> None:
        """Remove all recorded state for *target_name*."""
        self._state.pop(target_name, None)
