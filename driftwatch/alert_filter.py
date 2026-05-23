"""Alert suppression / deduplication filter.

Prevents the notifier from firing repeatedly for the same drifted target
until the drift is resolved or a cooldown window has elapsed.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class _SuppressionEntry:
    first_seen: float
    last_seen: float
    alert_count: int = 1


@dataclass
class AlertFilter:
    """Tracks per-target alert state and suppresses duplicate alerts.

    Args:
        cooldown_seconds: Minimum seconds between repeated alerts for the
            same drifted target.  Defaults to 300 (5 minutes).
    """

    cooldown_seconds: float = 300.0
    _state: Dict[str, _SuppressionEntry] = field(default_factory=dict, init=False, repr=False)

    def should_alert(self, target_name: str, *, _now: Optional[float] = None) -> bool:
        """Return True if an alert should be sent for *target_name*.

        The first occurrence always returns True.  Subsequent calls return
        True only once the cooldown window has elapsed since the last alert.
        """
        now = _now if _now is not None else time.monotonic()
        entry = self._state.get(target_name)

        if entry is None:
            self._state[target_name] = _SuppressionEntry(first_seen=now, last_seen=now)
            return True

        elapsed = now - entry.last_seen
        if elapsed >= self.cooldown_seconds:
            entry.last_seen = now
            entry.alert_count += 1
            return True

        return False

    def clear(self, target_name: str) -> None:
        """Remove suppression state for *target_name* (e.g. drift resolved)."""
        self._state.pop(target_name, None)

    def alert_count(self, target_name: str) -> int:
        """Return how many alerts have been sent for *target_name*."""
        entry = self._state.get(target_name)
        return entry.alert_count if entry is not None else 0

    def suppressed_targets(self) -> list[str]:
        """Return names of targets currently in the suppression window."""
        now = time.monotonic()
        return [
            name
            for name, entry in self._state.items()
            if (now - entry.last_seen) < self.cooldown_seconds
        ]
