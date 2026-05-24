"""Tests for driftwatch.drift_diff and driftwatch.diff_reporter."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from driftwatch.checker import DriftResult
from driftwatch.config import WatchTarget
from driftwatch.diff_reporter import annotate_summary, build_diff_report
from driftwatch.drift_diff import DiffResult, compute_diff, format_diff_report
from driftwatch.runner import RunSummary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LOCAL = b"line1\nline2\nline3\n"
REMOTE = b"line1\nLINE2 CHANGED\nline3\nline4 added\n"


def _target(name: str = "cfg") -> WatchTarget:
    return WatchTarget(name=name, local_path="/etc/cfg", remote_url="http://example.com/cfg")


def _drift_result(
    target: WatchTarget | None = None,
    local: bytes = LOCAL,
    remote: bytes = REMOTE,
) -> DriftResult:
    t = target or _target()
    r = MagicMock(spec=DriftResult)
    r.target = t
    r.drifted = True
    r.error = None
    r.local_content = local
    r.remote_content = remote
    return r


def _clean_result(target: WatchTarget | None = None) -> DriftResult:
    t = target or _target("clean")
    r = MagicMock(spec=DriftResult)
    r.target = t
    r.drifted = False
    r.error = None
    r.local_content = LOCAL
    r.remote_content = LOCAL
    return r


def _summary(results: list) -> RunSummary:
    s = MagicMock(spec=RunSummary)
    s.results = results
    return s


# ---------------------------------------------------------------------------
# compute_diff
# ---------------------------------------------------------------------------

def test_compute_diff_detects_changes():
    result = compute_diff("mycfg", LOCAL, REMOTE)
    assert result.has_diff is True
    assert result.target_name == "mycfg"


def test_compute_diff_no_diff_when_identical():
    result = compute_diff("mycfg", LOCAL, LOCAL)
    assert result.has_diff is False
    assert result.unified_diff == ""


def test_line_count_counts_changed_lines():
    result = compute_diff("mycfg", LOCAL, REMOTE)
    assert result.line_count > 0


def test_compute_diff_returns_diff_result_type():
    result = compute_diff("x", LOCAL, REMOTE)
    assert isinstance(result, DiffResult)


# ---------------------------------------------------------------------------
# format_diff_report
# ---------------------------------------------------------------------------

def test_format_diff_report_no_diff_message():
    result = compute_diff("x", LOCAL, LOCAL)
    report = format_diff_report(result)
    assert "No differences" in report


def test_format_diff_report_contains_target_name():
    result = compute_diff("myfile", LOCAL, REMOTE)
    report = format_diff_report(result)
    assert "myfile" in report


def test_format_diff_report_truncates_output():
    big_local = ("a\n" * 200).encode()
    big_remote = ("b\n" * 200).encode()
    result = compute_diff("big", big_local, big_remote)
    report = format_diff_report(result, max_lines=10)
    assert "truncated" in report


# ---------------------------------------------------------------------------
# annotate_summary / build_diff_report
# ---------------------------------------------------------------------------

def test_annotate_summary_attaches_diff_for_drifted():
    results = [_drift_result()]
    annotated = annotate_summary(_summary(results))
    assert annotated[0].diff is not None
    assert annotated[0].diff.has_diff is True


def test_annotate_summary_no_diff_for_clean():
    results = [_clean_result()]
    annotated = annotate_summary(_summary(results))
    assert annotated[0].diff is None


def test_build_diff_report_no_drift_message():
    report = build_diff_report(_summary([_clean_result()]))
    assert "No drift detected" in report


def test_build_diff_report_contains_drifted_target_name():
    t = _target("important.conf")
    report = build_diff_report(_summary([_drift_result(target=t)]))
    assert "important.conf" in report


def test_build_diff_report_header_shows_count():
    results = [_drift_result(_target("a")), _drift_result(_target("b"))]
    report = build_diff_report(_summary(results))
    assert "2 target(s)" in report
