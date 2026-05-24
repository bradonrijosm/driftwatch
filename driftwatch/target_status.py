"""Tracks the latest check status for each watched target."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from driftwatch.config import WatchTarget
from driftwatch.checker import DriftResult


class TargetStatus(str, enum.Enum):
    CLEAN = "clean"
    DRIFT = "drift"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class TargetStatusEntry:
    target: WatchTarget
    status: TargetStatus = TargetStatus.UNKNOWN
    last_message: str = ""


@dataclass
class StatusMap:
    """Mutable map from target local_path -> TargetStatusEntry."""
    _entries: Dict[str, TargetStatusEntry] = field(default_factory=dict)

    def update(self, target: WatchTarget, result: DriftResult) -> None:
        if result.error:
            status = TargetStatus.ERROR
            message = result.error
        elif result.drifted:
            status = TargetStatus.DRIFT
            message = "drift detected"
        else:
            status = TargetStatus.CLEAN
            message = "ok"
        self._entries[target.local_path] = TargetStatusEntry(
            target=target, status=status, last_message=message
        )

    def get(self, local_path: str) -> Optional[TargetStatusEntry]:
        return self._entries.get(local_path)

    def entries(self) -> List[TargetStatusEntry]:
        return list(self._entries.values())

    def all_clean(self) -> bool:
        if not self._entries:
            return True
        return all(e.status == TargetStatus.CLEAN for e in self._entries.values())

    def clear(self) -> None:
        self._entries.clear()
