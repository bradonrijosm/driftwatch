"""Drift scoring: assigns a numeric severity score to drift results."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from driftwatch.checker import DriftResult


# Weights used when computing the aggregate score.
_DRIFT_WEIGHT = 10
_ERROR_WEIGHT = 5
_OK_WEIGHT = 0


@dataclass(frozen=True)
class TargetScore:
    """Score for a single watch-target."""

    target_name: str
    score: int          # 0 = clean, >0 = degraded
    reason: str

    @property
    def is_clean(self) -> bool:
        return self.score == 0


@dataclass(frozen=True)
class AggregateScore:
    """Roll-up score across all targets."""

    total: int
    target_scores: tuple[TargetScore, ...]

    @property
    def is_clean(self) -> bool:
        return self.total == 0

    @property
    def worst(self) -> TargetScore | None:
        if not self.target_scores:
            return None
        return max(self.target_scores, key=lambda ts: ts.score)


def score_result(result: DriftResult) -> TargetScore:
    """Return a :class:`TargetScore` for a single *result*."""
    name = result.target.name
    if result.error:
        return TargetScore(target_name=name, score=_ERROR_WEIGHT, reason=f"error: {result.error}")
    if result.drifted:
        return TargetScore(target_name=name, score=_DRIFT_WEIGHT, reason="content mismatch")
    return TargetScore(target_name=name, score=_OK_WEIGHT, reason="ok")


def aggregate_scores(results: Sequence[DriftResult]) -> AggregateScore:
    """Compute an :class:`AggregateScore` from a collection of results."""
    scores = tuple(score_result(r) for r in results)
    total = sum(ts.score for ts in scores)
    return AggregateScore(total=total, target_scores=scores)
