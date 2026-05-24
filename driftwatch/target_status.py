"""Aggregate per-target status across a run summary for quick lookup."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

from driftwatch.checker import DriftResult
from driftwatch.config import WatchTarget
from driftwatch.runner import RunSummary


class TargetStatus(str, Enum):
    CLEAN = "clean"
    DRIFTED = "drifted"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class TargetStatusEntry:
    target: WatchTarget
    status: TargetStatus
    detail: str = ""


@dataclass
class StatusMap:
    entries: Dict[str, TargetStatusEntry] = field(default_factory=dict)

    def get(self, local_path: str) -> TargetStatusEntry | None:
        return self.entries.get(local_path)

    def all_clean(self) -> bool:
        return all(
            e.status == TargetStatus.CLEAN for e in self.entries.values()
        )

    def by_status(self, status: TargetStatus) -> List[TargetStatusEntry]:
        return [e for e in self.entries.values() if e.status == status]


def _classify(result: DriftResult) -> tuple[TargetStatus, str]:
    if result.error:
        return TargetStatus.ERROR, result.error
    if result.drifted:
        detail = (
            f"local={result.local_checksum} remote={result.remote_checksum}"
        )
        return TargetStatus.DRIFTED, detail
    return TargetStatus.CLEAN, ""


def build_status_map(summary: RunSummary) -> StatusMap:
    """Build a StatusMap from a completed RunSummary."""
    entries: Dict[str, TargetStatusEntry] = {}
    for target, result in zip(summary.targets, summary.results):
        status, detail = _classify(result)
        entries[target.local_path] = TargetStatusEntry(
            target=target, status=status, detail=detail
        )
    return StatusMap(entries=entries)
