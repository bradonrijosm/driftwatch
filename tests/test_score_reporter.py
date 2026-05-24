"""Tests for driftwatch.score_reporter."""
from __future__ import annotations

import io

import pytest

from driftwatch.checker import DriftResult
from driftwatch.config import WatchTarget
from driftwatch.drift_score import aggregate_scores
from driftwatch.score_reporter import build_score_report, print_score_report


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _target(name: str) -> WatchTarget:
    return WatchTarget(name=name, local_path="/tmp/f", remote_url="https://example.com/f")


def _ok(name: str) -> DriftResult:
    return DriftResult(target=_target(name), drifted=False, error=None)


def _drift(name: str) -> DriftResult:
    return DriftResult(target=_target(name), drifted=True, error=None)


def _error(name: str) -> DriftResult:
    return DriftResult(target=_target(name), drifted=False, error="timeout")


# ---------------------------------------------------------------------------
# build_score_report
# ---------------------------------------------------------------------------

def test_header_present():
    agg = aggregate_scores([_ok("a")])
    report = build_score_report(agg)
    assert any("Drift Score Report" in line for line in report.lines)


def test_clean_summary_label():
    agg = aggregate_scores([_ok("a"), _ok("b")])
    report = build_score_report(agg)
    assert any("CLEAN" in line for line in report.lines)


def test_degraded_summary_label():
    agg = aggregate_scores([_drift("a")])
    report = build_score_report(agg)
    assert any("DEGRADED" in line for line in report.lines)


def test_target_name_appears_in_report():
    agg = aggregate_scores([_ok("my-service-config")])
    report = build_score_report(agg)
    assert any("my-service-config" in line for line in report.lines)


def test_worst_offender_shown_when_degraded():
    agg = aggregate_scores([_drift("bad-target"), _ok("good-target")])
    report = build_score_report(agg)
    assert any("bad-target" in line and "Worst offender" in line for line in report.lines)


def test_no_worst_offender_line_when_clean():
    agg = aggregate_scores([_ok("a"), _ok("b")])
    report = build_score_report(agg)
    assert not any("Worst offender" in line for line in report.lines)


def test_score_tag_present_for_each_target():
    agg = aggregate_scores([_drift("x"), _error("y"), _ok("z")])
    report = build_score_report(agg)
    score_lines = [l for l in report.lines if "score=" in l]
    assert len(score_lines) == 3


def test_targets_sorted_highest_score_first():
    agg = aggregate_scores([_ok("clean"), _drift("drifted"), _error("errored")])
    report = build_score_report(agg)
    score_lines = [l for l in report.lines if "score=" in l]
    # drifted(10) should appear before errored(5) before clean(0)
    names_in_order = []
    for line in score_lines:
        for name in ("drifted", "errored", "clean"):
            if name in line:
                names_in_order.append(name)
    assert names_in_order == ["drifted", "errored", "clean"]


# ---------------------------------------------------------------------------
# print_score_report
# ---------------------------------------------------------------------------

def test_print_score_report_writes_to_stream():
    agg = aggregate_scores([_ok("a")])
    buf = io.StringIO()
    print_score_report(agg, out=buf)
    output = buf.getvalue()
    assert "Drift Score Report" in output
    assert "a" in output


def test_print_score_report_empty_targets():
    agg = aggregate_scores([])
    buf = io.StringIO()
    print_score_report(agg, out=buf)
    output = buf.getvalue()
    assert "CLEAN" in output
