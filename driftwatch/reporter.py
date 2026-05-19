"""Human-readable summary reporter for drift check results."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TextIO

from driftwatch.checker import DriftResult
from driftwatch.runner import RunSummary


@dataclass
class ReportStats:
    total: int = 0
    clean: int = 0
    drifted: int = 0
    errors: int = 0

    @property
    def has_issues(self) -> bool:
        return self.drifted > 0 or self.errors > 0


def _status_line(result: DriftResult) -> str:
    """Return a single-line status string for one target result."""
    target_name = result.target.local_path
    if result.error:
        return f"  [ERROR]  {target_name}: {result.error}"
    if result.drifted:
        return f"  [DRIFT]  {target_name}: checksum mismatch"
    return f"  [OK]     {target_name}"


def build_report(summary: RunSummary) -> tuple[str, ReportStats]:
    """Build a full text report from a RunSummary.

    Returns the report string and aggregated ReportStats.
    """
    stats = ReportStats(total=len(summary.results))
    lines: list[str] = []

    lines.append(f"DriftWatch Report — {stats.total} target(s) checked")
    lines.append("-" * 50)

    for result in summary.results:
        lines.append(_status_line(result))
        if result.error:
            stats.errors += 1
        elif result.drifted:
            stats.drifted += 1
        else:
            stats.clean += 1

    lines.append("-" * 50)
    lines.append(
        f"Summary: {stats.clean} clean, {stats.drifted} drifted, {stats.errors} error(s)"
    )

    return "\n".join(lines), stats


def print_report(summary: RunSummary, stream: TextIO = sys.stdout) -> ReportStats:
    """Print a human-readable report to *stream* and return stats."""
    report, stats = build_report(summary)
    print(report, file=stream)
    return stats
