"""Analyze drift trends over recent history to detect recurring or worsening targets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from driftwatch.history import DriftEvent


@dataclass(frozen=True)
class TargetTrend:
    target_name: str
    total_events: int
    drift_count: int
    error_count: int
    ok_count: int
    drift_rate: float  # 0.0 – 1.0

    @property
    def is_stable(self) -> bool:
        """True when no drift or errors were recorded."""
        return self.drift_count == 0 and self.error_count == 0

    @property
    def is_degrading(self) -> bool:
        """True when drift rate exceeds 50 %."""
        return self.drift_rate > 0.5


@dataclass
class TrendReport:
    trends: list[TargetTrend] = field(default_factory=list)

    @property
    def degrading_targets(self) -> list[TargetTrend]:
        return [t for t in self.trends if t.is_degrading]

    @property
    def unstable_targets(self) -> list[TargetTrend]:
        return [t for t in self.trends if not t.is_stable]


def analyze_trends(events: Sequence[DriftEvent]) -> TrendReport:
    """Group *events* by target name and compute per-target trend statistics."""
    grouped: dict[str, list[DriftEvent]] = {}
    for ev in events:
        grouped.setdefault(ev.target_name, []).append(ev)

    trends: list[TargetTrend] = []
    for name, evs in grouped.items():
        total = len(evs)
        drift_count = sum(1 for e in evs if e.status == "drift")
        error_count = sum(1 for e in evs if e.status == "error")
        ok_count = sum(1 for e in evs if e.status == "ok")
        drift_rate = (drift_count + error_count) / total if total else 0.0
        trends.append(
            TargetTrend(
                target_name=name,
                total_events=total,
                drift_count=drift_count,
                error_count=error_count,
                ok_count=ok_count,
                drift_rate=round(drift_rate, 4),
            )
        )

    # Deterministic order: worst drift rate first, then alphabetical
    trends.sort(key=lambda t: (-t.drift_rate, t.target_name))
    return TrendReport(trends=trends)
