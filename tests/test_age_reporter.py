"""Tests for driftwatch.age_reporter."""
from __future__ import annotations

from driftwatch.age_reporter import build_age_report, _fmt_age, AgeReportLine
from driftwatch.drift_age import DriftAgeTracker
from driftwatch.checker import DriftResult
from driftwatch.config import WatchTarget
from driftwatch.runner import RunSummary


def _target(name: str = "app") -> WatchTarget:
    return WatchTarget(name=name, local_path="/etc/app.conf", remote_url="https://example.com/app.conf")


def _ok(target: WatchTarget) -> DriftResult:
    return DriftResult(target=target, drifted=False, error=None)


def _drift(target: WatchTarget) -> DriftResult:
    return DriftResult(target=target, drifted=True, error=None)


def _summary(*results: DriftResult) -> RunSummary:
    return RunSummary(results=list(results))


# --- _fmt_age ---

def test_fmt_age_seconds():
    assert _fmt_age(45) == "45s"


def test_fmt_age_minutes():
    assert _fmt_age(125) == "2m 5s"


def test_fmt_age_hours():
    assert _fmt_age(3661) == "1h 1m"


# --- AgeReportLine ---

def test_report_line_str_contains_name():
    line = AgeReportLine(name="myapp", status="ok", age_seconds=30, transitions=0)
    assert "myapp" in str(line)


def test_report_line_str_contains_status():
    line = AgeReportLine(name="myapp", status="drift", age_seconds=90, transitions=2)
    assert "drift" in str(line)


def test_report_line_str_contains_transitions():
    line = AgeReportLine(name="myapp", status="ok", age_seconds=10, transitions=3)
    assert "transitions=3" in str(line)


# --- build_age_report ---

def test_header_present():
    tracker = DriftAgeTracker()
    t = _target()
    r = _ok(t)
    tracker.update(t, r, now=0.0)
    report = build_age_report(tracker, _summary(r))
    assert report[0] == "=== Drift Age Report ==="


def test_placeholder_when_no_data():
    tracker = DriftAgeTracker()
    t = _target()
    r = _ok(t)  # never updated in tracker
    report = build_age_report(tracker, _summary(r))
    assert any("no age data" in line for line in report)


def test_report_contains_target_name():
    tracker = DriftAgeTracker()
    t = _target("myservice")
    r = _ok(t)
    tracker.update(t, r, now=0.0)
    report = build_age_report(tracker, _summary(r))
    assert any("myservice" in line for line in report)


def test_drift_icon_present():
    tracker = DriftAgeTracker()
    t = _target()
    r = _drift(t)
    tracker.update(t, r, now=0.0)
    report = build_age_report(tracker, _summary(r))
    combined = " ".join(report)
    assert "\u26a0" in combined


def test_longest_age_first():
    tracker = DriftAgeTracker()
    t1 = _target("alpha")
    t2 = _target("beta")
    r1 = _ok(t1)
    r2 = _ok(t2)
    tracker.update(t1, r1, now=0.0)    # older
    tracker.update(t2, r2, now=500.0)  # newer
    report = build_age_report(tracker, _summary(r1, r2), )
    # alpha (older) should appear before beta (newer)
    lines = [l for l in report if "alpha" in l or "beta" in l]
    assert lines[0].find("alpha") >= 0 or "alpha" in lines[0]
