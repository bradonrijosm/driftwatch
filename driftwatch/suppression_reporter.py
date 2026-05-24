"""Human-readable report of which targets are suppressed and why."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from driftwatch.config import WatchTarget
from driftwatch.drift_suppression import SuppressionList


@dataclass
class SuppressionReportLine:
    target_name: str
    suppressed: bool
    reason: str | None


def build_suppression_report(
    targets: Sequence[WatchTarget],
    suppression_list: SuppressionList,
) -> list[SuppressionReportLine]:
    """Return one line per target describing its suppression status."""
    lines: list[SuppressionReportLine] = []
    for target in targets:
        reason = suppression_list.suppressed_reason(target)
        lines.append(
            SuppressionReportLine(
                target_name=target.name,
                suppressed=reason is not None,
                reason=reason,
            )
        )
    return lines


def format_suppression_report(
    lines: list[SuppressionReportLine],
) -> str:
    """Return a formatted multi-line string suitable for CLI output."""
    if not lines:
        return "No targets configured.\n"

    header = f"{'TARGET':<30}  {'SUPPRESSED':<10}  REASON"
    separator = "-" * len(header)
    rows = [header, separator]

    for line in lines:
        icon = "\u23f8  yes" if line.suppressed else "\u25b6  no "
        reason_str = line.reason or ""
        rows.append(f"{line.target_name:<30}  {icon:<10}  {reason_str}")

    return "\n".join(rows) + "\n"


def print_suppression_report(
    targets: Sequence[WatchTarget],
    suppression_list: SuppressionList,
) -> None:
    """Build and print the suppression report to stdout."""
    lines = build_suppression_report(targets, suppression_list)
    print(format_suppression_report(lines), end="")
