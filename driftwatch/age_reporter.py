"""Formats a human-readable report of per-target drift ages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from driftwatch.drift_age import AgeEntry, DriftAgeTracker
from driftwatch.runner import RunSummary

_ICONS = {"ok": "\u2705", "drift": "\u26a0\ufe0f ", "error": "\u274c"}


@dataclass
class AgeReportLine:
    name: str
    status: str
    age_seconds: float
    transitions: int

    def __str__(self) -> str:
        icon = _ICONS.get(self.status, "?")
        age_str = _fmt_age(self.age_seconds)
        return f"  {icon} {self.name:<30} {self.status:<6}  age={age_str}  transitions={self.transitions}"


def _fmt_age(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"


def build_age_report(tracker: DriftAgeTracker, summary: RunSummary) -> List[str]:
    """Return a list of report lines for every target in *summary*."""
    lines: List[str] = ["=== Drift Age Report ==="]
    rows: List[Tuple[str, AgeEntry]] = []

    for result in summary.results:
        entry = tracker.get(result.target)
        if entry is None:
            continue
        rows.append((result.target.name, entry))

    if not rows:
        lines.append("  (no age data available)")
        return lines

    for name, entry in sorted(rows, key=lambda t: t[1].age_seconds(), reverse=True):
        line = AgeReportLine(
            name=name,
            status=entry.status,
            age_seconds=entry.age_seconds(),
            transitions=entry.transitions,
        )
        lines.append(str(line))
    return lines


def print_age_report(tracker: DriftAgeTracker, summary: RunSummary) -> None:
    for line in build_age_report(tracker, summary):
        print(line)
