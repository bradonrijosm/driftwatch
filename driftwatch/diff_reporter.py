"""Attach unified diffs to a RunSummary and produce a diff-enriched report."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from driftwatch.checker import DriftResult
from driftwatch.drift_diff import DiffResult, compute_diff, format_diff_report
from driftwatch.runner import RunSummary


@dataclass
class AnnotatedResult:
    drift_result: DriftResult
    diff: Optional[DiffResult] = None

    @property
    def target_name(self) -> str:
        return self.drift_result.target.name


def annotate_summary(
    summary: RunSummary,
    context_lines: int = 3,
) -> list[AnnotatedResult]:
    """For every drifted target in *summary*, compute and attach a DiffResult."""
    annotated: list[AnnotatedResult] = []
    for result in summary.results:
        if result.drifted and result.local_content is not None and result.remote_content is not None:
            diff = compute_diff(
                result.target.name,
                result.local_content,
                result.remote_content,
                context_lines=context_lines,
            )
            annotated.append(AnnotatedResult(drift_result=result, diff=diff))
        else:
            annotated.append(AnnotatedResult(drift_result=result))
    return annotated


def build_diff_report(
    summary: RunSummary,
    context_lines: int = 3,
    max_lines_per_diff: Optional[int] = 50,
) -> str:
    """Return a multi-target diff report string for all drifted targets."""
    annotated = annotate_summary(summary, context_lines=context_lines)
    drifted = [a for a in annotated if a.diff is not None and a.diff.has_diff]

    if not drifted:
        return "No drift detected — all targets match remote."

    sections = [f"Drift Diff Report  ({len(drifted)} target(s) drifted)\n" + "=" * 60]
    for item in drifted:
        assert item.diff is not None
        sections.append(format_diff_report(item.diff, max_lines=max_lines_per_diff))

    return "\n\n".join(sections)


def print_diff_report(summary: RunSummary, **kwargs: object) -> None:  # pragma: no cover
    print(build_diff_report(summary, **kwargs))  # type: ignore[arg-type]
