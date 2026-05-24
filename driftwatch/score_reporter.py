"""Human-readable report built from an :class:`AggregateScore`."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TextIO
import sys

from driftwatch.drift_score import AggregateScore, TargetScore

_CLEAN_ICON = "\u2705"   # ✅
_DRIFT_ICON = "\u26a0\ufe0f"  # ⚠️
_ERROR_ICON = "\u274c"  # ❌


def _icon(ts: TargetScore) -> str:
    if ts.score == 0:
        return _CLEAN_ICON
    if ts.score >= 10:
        return _DRIFT_ICON
    return _ERROR_ICON


def _fmt_target_line(ts: TargetScore) -> str:
    icon = _icon(ts)
    score_tag = f"[score={ts.score}]"
    return f"  {icon}  {ts.target_name:<30} {score_tag:<12}  {ts.reason}"


@dataclass(frozen=True)
class ScoreReport:
    """Rendered score report ready for display."""

    lines: tuple[str, ...]

    def __str__(self) -> str:  # pragma: no cover
        return "\n".join(self.lines)


def build_score_report(agg: AggregateScore) -> ScoreReport:
    """Build a :class:`ScoreReport` from *agg*."""
    header = "=== Drift Score Report ==="
    summary = f"Aggregate score: {agg.total}  ({'CLEAN' if agg.is_clean else 'DEGRADED'})"

    target_lines = [_fmt_target_line(ts) for ts in sorted(
        agg.target_scores, key=lambda ts: ts.score, reverse=True
    )]

    worst = agg.worst
    footer_parts = []
    if worst and not worst.is_clean:
        footer_parts.append(f"Worst offender: {worst.target_name} (score={worst.score})")

    lines: list[str] = [header, summary, ""] + target_lines
    if footer_parts:
        lines += [""] + footer_parts

    return ScoreReport(lines=tuple(lines))


def print_score_report(agg: AggregateScore, out: TextIO = sys.stdout) -> None:
    """Print a score report to *out* (default stdout)."""
    report = build_score_report(agg)
    for line in report.lines:
        print(line, file=out)
