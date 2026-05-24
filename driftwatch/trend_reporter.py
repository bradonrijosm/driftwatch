"""Format a TrendReport for human-readable console output."""

from __future__ import annotations

from driftwatch.trend_analyzer import TrendReport, TargetTrend

_ICON_STABLE = "✅"
_ICON_DEGRADING = "🔴"
_ICON_UNSTABLE = "⚠️"


def _icon(trend: TargetTrend) -> str:
    if trend.is_degrading:
        return _ICON_DEGRADING
    if not trend.is_stable:
        return _ICON_UNSTABLE
    return _ICON_STABLE


def _fmt_trend_line(trend: TargetTrend) -> str:
    pct = f"{trend.drift_rate * 100:.1f}%"
    return (
        f"  {_icon(trend)} {trend.target_name:<40} "
        f"total={trend.total_events:>4}  "
        f"ok={trend.ok_count:>4}  "
        f"drift={trend.drift_count:>4}  "
        f"error={trend.error_count:>4}  "
        f"rate={pct:>6}"
    )


def build_trend_report(report: TrendReport, window_label: str = "recent") -> str:
    lines: list[str] = [
        f"Drift Trend Report ({window_label})",
        "=" * 72,
    ]

    if not report.trends:
        lines.append("  No history events found.")
        return "\n".join(lines)

    for trend in report.trends:
        lines.append(_fmt_trend_line(trend))

    lines.append("-" * 72)
    degrading = len(report.degrading_targets)
    unstable = len(report.unstable_targets)
    lines.append(
        f"  Targets: {len(report.trends)}  "
        f"Degrading (>50 %): {degrading}  "
        f"Unstable: {unstable}"
    )
    return "\n".join(lines)


def print_trend_report(report: TrendReport, window_label: str = "recent") -> None:  # pragma: no cover
    print(build_trend_report(report, window_label=window_label))
