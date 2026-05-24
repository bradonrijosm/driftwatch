"""Tracks how long each target has been in its current drift state."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from driftwatch.checker import DriftResult
from driftwatch.config import WatchTarget


@dataclass
class AgeEntry:
    status: str          # "ok", "drift", or "error"
    since: float         # epoch seconds when status last changed
    transitions: int = 0 # number of status changes observed

    def age_seconds(self, now: Optional[float] = None) -> float:
        """Return how many seconds the target has been in the current status."""
        return (now if now is not None else time.time()) - self.since


@dataclass
class DriftAgeTracker:
    """Maintains per-target age entries, updating on each run result."""
    _entries: Dict[str, AgeEntry] = field(default_factory=dict)

    def update(self, target: WatchTarget, result: DriftResult, now: Optional[float] = None) -> AgeEntry:
        """Record the latest result for *target* and return the updated AgeEntry."""
        ts = now if now is not None else time.time()
        new_status = _status_of(result)
        key = target.name

        existing = self._entries.get(key)
        if existing is None or existing.status != new_status:
            transitions = 0 if existing is None else existing.transitions + 1
            self._entries[key] = AgeEntry(status=new_status, since=ts, transitions=transitions)
        return self._entries[key]

    def get(self, target: WatchTarget) -> Optional[AgeEntry]:
        """Return the current AgeEntry for *target*, or None if unseen."""
        return self._entries.get(target.name)

    def all_entries(self) -> Dict[str, AgeEntry]:
        return dict(self._entries)


def _status_of(result: DriftResult) -> str:
    if result.error:
        return "error"
    if result.drifted:
        return "drift"
    return "ok"
