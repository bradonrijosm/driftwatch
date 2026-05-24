"""Tests for trend_analyzer and trend_reporter."""

from __future__ import annotations

import datetime
from typing import Sequence

import pytest

from driftwatch.history import DriftEvent
from driftwatch.trend_analyzer import TargetTrend, TrendReport, analyze_trends
from driftwatch.trend_reporter import build_trend_report


def _ev(name: str, status: str, offset_s: int = 0) -> DriftEvent:
    ts = datetime.datetime(2024, 6, 1, 12, 0, 0) + datetime.timedelta(seconds=offset_s)
    return DriftEvent(id=offset_s, target_name=name, status=status, timestamp=ts, detail="")


# ---------------------------------------------------------------------------
# TargetTrend properties
# ---------------------------------------------------------------------------

class TestTargetTrend:
    def _make(self, drift=0, error=0, ok=4) -> TargetTrend:
        total = drift + error + ok
        rate = (drift + error) / total if total else 0.0
        return TargetTrend(
            target_name="t", total_events=total,
            drift_count=drift, error_count=error, ok_count=ok,
            drift_rate=rate,
        )

    def test_stable_when_no_issues(self):
        assert self._make(drift=0, error=0).is_stable is True

    def test_not_stable_with_drift(self):
        assert self._make(drift=1).is_stable is False

    def test_not_stable_with_error(self):
        assert self._make(error=1).is_stable is False

    def test_degrading_above_half(self):
        assert self._make(drift=3, ok=2).is_degrading is True

    def test_not_degrading_at_half(self):
        # exactly 0.5 is NOT degrading (> 0.5 required)
        t = self._make(drift=2, ok=2)
        assert t.is_degrading is False


# ---------------------------------------------------------------------------
# analyze_trends
# ---------------------------------------------------------------------------

def test_empty_events_returns_empty_report():
    report = analyze_trends([])
    assert report.trends == []


def test_single_target_all_ok():
    events = [_ev("cfg", "ok", i) for i in range(5)]
    report = analyze_trends(events)
    assert len(report.trends) == 1
    t = report.trends[0]
    assert t.ok_count == 5
    assert t.drift_count == 0
    assert t.drift_rate == 0.0
    assert t.is_stable is True


def test_mixed_statuses_counted_correctly():
    events = [
        _ev("a", "ok", 0), _ev("a", "ok", 1),
        _ev("a", "drift", 2), _ev("a", "error", 3),
    ]
    report = analyze_trends(events)
    t = report.trends[0]
    assert t.ok_count == 2
    assert t.drift_count == 1
    assert t.error_count == 1
    assert t.drift_rate == pytest.approx(0.5)


def test_multiple_targets_sorted_by_drift_rate_desc():
    events = [
        _ev("clean", "ok"), _ev("clean", "ok"),
        _ev("bad", "drift"), _ev("bad", "drift"), _ev("bad", "ok"),
    ]
    report = analyze_trends(events)
    assert report.trends[0].target_name == "bad"
    assert report.trends[1].target_name == "clean"


def test_degrading_targets_property():
    events = [_ev("x", "drift", i) for i in range(4)] + [_ev("x", "ok", 10)]
    report = analyze_trends(events)
    assert len(report.degrading_targets) == 1


def test_unstable_targets_includes_error_only():
    events = [_ev("y", "error"), _ev("y", "ok"), _ev("y", "ok")]
    report = analyze_trends(events)
    assert len(report.unstable_targets) == 1


# ---------------------------------------------------------------------------
# build_trend_report
# ---------------------------------------------------------------------------

def test_build_report_empty_contains_placeholder():
    text = build_trend_report(TrendReport())
    assert "No history" in text


def test_build_report_header_present():
    report = analyze_trends([_ev("cfg", "ok")])
    text = build_trend_report(report, window_label="last 24 h")
    assert "last 24 h" in text
    assert "Drift Trend Report" in text


def test_build_report_contains_target_name():
    report = analyze_trends([_ev("my_target", "drift")])
    text = build_trend_report(report)
    assert "my_target" in text


def test_build_report_summary_line_counts():
    events = (
        [_ev("a", "drift", i) for i in range(3)]
        + [_ev("b", "ok", i + 10) for i in range(3)]
    )
    report = analyze_trends(events)
    text = build_trend_report(report)
    assert "Targets: 2" in text
    assert "Degrading" in text
