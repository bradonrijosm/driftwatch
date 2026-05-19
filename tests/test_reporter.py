"""Tests for driftwatch.reporter."""

from __future__ import annotations

import io
from unittest.mock import MagicMock

import pytest

from driftwatch.checker import DriftResult
from driftwatch.reporter import ReportStats, build_report, print_report
from driftwatch.runner import RunSummary


def _make_target(path: str = "/etc/app.conf") -> MagicMock:
    t = MagicMock()
    t.local_path = path
    return t


def _make_result(path: str, drifted: bool = False, error: str | None = None) -> DriftResult:
    return DriftResult(target=_make_target(path), drifted=drifted, error=error)


def _make_summary(*results: DriftResult) -> RunSummary:
    summary = MagicMock(spec=RunSummary)
    summary.results = list(results)
    return summary


class TestReportStats:
    def test_has_issues_false_when_all_clean(self):
        stats = ReportStats(total=2, clean=2)
        assert not stats.has_issues

    def test_has_issues_true_when_drifted(self):
        stats = ReportStats(total=1, drifted=1)
        assert stats.has_issues

    def test_has_issues_true_when_errors(self):
        stats = ReportStats(total=1, errors=1)
        assert stats.has_issues


class TestBuildReport:
    def test_report_contains_target_path(self):
        summary = _make_summary(_make_result("/etc/app.conf"))
        report, _ = build_report(summary)
        assert "/etc/app.conf" in report

    def test_clean_result_shows_ok(self):
        summary = _make_summary(_make_result("/etc/app.conf", drifted=False))
        report, stats = build_report(summary)
        assert "[OK]" in report
        assert stats.clean == 1
        assert stats.drifted == 0
        assert stats.errors == 0

    def test_drifted_result_shows_drift(self):
        summary = _make_summary(_make_result("/etc/app.conf", drifted=True))
        report, stats = build_report(summary)
        assert "[DRIFT]" in report
        assert stats.drifted == 1

    def test_error_result_shows_error(self):
        summary = _make_summary(_make_result("/etc/app.conf", error="file not found"))
        report, stats = build_report(summary)
        assert "[ERROR]" in report
        assert "file not found" in report
        assert stats.errors == 1

    def test_summary_line_counts_are_correct(self):
        summary = _make_summary(
            _make_result("/a"),
            _make_result("/b", drifted=True),
            _make_result("/c", error="timeout"),
        )
        report, stats = build_report(summary)
        assert stats.total == 3
        assert stats.clean == 1
        assert stats.drifted == 1
        assert stats.errors == 1
        assert "3 target(s)" in report


class TestPrintReport:
    def test_print_report_writes_to_stream(self):
        summary = _make_summary(_make_result("/etc/app.conf"))
        stream = io.StringIO()
        stats = print_report(summary, stream=stream)
        output = stream.getvalue()
        assert "/etc/app.conf" in output
        assert isinstance(stats, ReportStats)

    def test_print_report_returns_stats_with_has_issues_false(self):
        summary = _make_summary(_make_result("/etc/app.conf"))
        stats = print_report(summary, stream=io.StringIO())
        assert not stats.has_issues
