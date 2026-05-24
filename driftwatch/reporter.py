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


def print_drifted(summary: RunSummary, stream: TextIO = sys.stdout) -> ReportStats:
    """Print only drifted and errored targets to *stream* and return stats.

    Useful for a concise view when most targets are clean and only failures
    are of interest (e.g. in CI log output).
    """
    _, stats = build_report(summary)
    issues = [r for r in summary.results if r.error or r.drifted]

    if not issues:
        print("DriftWatch: all targets clean.", file=stream)
        return stats

    print(f"DriftWatch: {len(issues)} issue(s) detected", file=stream)
    print("-" * 50, file=stream)
    for result in issues:
        print(_status_line(result), file=stream)
    print("-" * 50, file=stream)
    return stats
