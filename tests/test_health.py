"""Tests for driftwatch.health."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from driftwatch.health import HealthReporter, HealthStatus
from driftwatch.metrics import MetricsCollector, MetricsSnapshot
from driftwatch.target_status import StatusMap, TargetStatus, TargetStatusEntry


def _make_snapshot(**overrides) -> MetricsSnapshot:
    base = {"checks_run": 0, "drift_detected": 0, "fetch_errors": 0}
    base.update(overrides)
    return MetricsSnapshot(base)


def _make_status_map(entries=None):
    sm = MagicMock(spec=StatusMap)
    sm.entries.return_value = entries or []
    return sm


def _make_reporter(snapshot_data=None, entries=None) -> HealthReporter:
    metrics = MagicMock(spec=MetricsCollector)
    metrics.snapshot.return_value = _make_snapshot(**(snapshot_data or {}))
    status_map = _make_status_map(entries)
    return HealthReporter(metrics=metrics, status_map=status_map)


class TestHealthStatus:
    def test_as_dict_contains_all_keys(self):
        hs = HealthStatus(
            healthy=True,
            uptime_seconds=42.5,
            checks_run=10,
            drift_count=0,
            error_count=0,
            target_statuses={},
        )
        d = hs.as_dict()
        assert "healthy" in d
        assert "uptime_seconds" in d
        assert "checks_run" in d
        assert "drift_count" in d
        assert "error_count" in d
        assert "target_statuses" in d
        assert "timestamp" in d

    def test_uptime_is_rounded(self):
        hs = HealthStatus(
            healthy=True, uptime_seconds=1.23456789,
            checks_run=1, drift_count=0, error_count=0, target_statuses={},
        )
        assert hs.as_dict()["uptime_seconds"] == 1.23


def test_healthy_when_no_drift_or_errors():
    reporter = _make_reporter({"checks_run": 5, "drift_detected": 0, "fetch_errors": 0})
    snap = reporter.snapshot()
    assert snap.healthy is True


def test_unhealthy_when_drift_detected():
    reporter = _make_reporter({"checks_run": 5, "drift_detected": 1, "fetch_errors": 0})
    snap = reporter.snapshot()
    assert snap.healthy is False


def test_unhealthy_when_errors_present():
    reporter = _make_reporter({"checks_run": 3, "drift_detected": 0, "fetch_errors": 2})
    snap = reporter.snapshot()
    assert snap.healthy is False


def test_snapshot_includes_target_statuses():
    target = MagicMock()
    target.local_path = "/etc/app.conf"
    entry = MagicMock(spec=TargetStatusEntry)
    entry.target = target
    entry.status = TargetStatus.CLEAN

    reporter = _make_reporter(entries=[entry])
    snap = reporter.snapshot()
    assert snap.target_statuses == {"/etc/app.conf": TargetStatus.CLEAN.value}


def test_uptime_increases_over_time():
    reporter = _make_reporter()
    reporter.reset_start_time()
    time.sleep(0.05)
    snap = reporter.snapshot()
    assert snap.uptime_seconds >= 0.04


def test_checks_run_reflected_in_snapshot():
    reporter = _make_reporter({"checks_run": 42})
    snap = reporter.snapshot()
    assert snap.checks_run == 42
