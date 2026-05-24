"""Lightweight in-process metrics counters for DriftWatch."""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict


@dataclass
class MetricsSnapshot:
    """Immutable point-in-time view of collected counters."""

    counters: Dict[str, int]

    def get(self, name: str, default: int = 0) -> int:
        return self.counters.get(name, default)

    def __repr__(self) -> str:  # pragma: no cover
        pairs = ", ".join(f"{k}={v}" for k, v in sorted(self.counters.items()))
        return f"MetricsSnapshot({pairs})"


@dataclass
class MetricsCollector:
    """Thread-safe counter-based metrics collector."""

    _counters: Dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def increment(self, name: str, amount: int = 1) -> None:
        """Increment a named counter by *amount* (default 1)."""
        if amount < 0:
            raise ValueError(f"amount must be >= 0, got {amount}")
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    def reset(self, name: str) -> None:
        """Reset a single counter to zero."""
        with self._lock:
            self._counters[name] = 0

    def reset_all(self) -> None:
        """Reset every counter to zero."""
        with self._lock:
            self._counters.clear()

    def snapshot(self) -> MetricsSnapshot:
        """Return an immutable copy of the current counters."""
        with self._lock:
            return MetricsSnapshot(counters=dict(self._counters))

    def get(self, name: str, default: int = 0) -> int:
        """Return the current value of a counter without taking a full snapshot."""
        with self._lock:
            return self._counters.get(name, default)


# Module-level default collector used by the rest of the application.
default_collector: MetricsCollector = MetricsCollector()


def increment(name: str, amount: int = 1) -> None:  # noqa: D401
    """Increment *name* on the default collector."""
    default_collector.increment(name, amount)


def snapshot() -> MetricsSnapshot:
    """Return a snapshot from the default collector."""
    return default_collector.snapshot()


def reset_all() -> None:
    """Reset the default collector (useful in tests)."""
    default_collector.reset_all()
