"""Tests for driftwatch.scheduler."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.config import DriftWatchConfig, WatchTarget
from driftwatch.runner import RunSummary
from driftwatch.scheduler import SchedulerStats, run_loop


def _make_config(interval: float = 30.0) -> DriftWatchConfig:
    target = WatchTarget(
        name="cfg",
        local_path="/etc/app/config.yaml",
        remote_url="https://example.com/config.yaml",
    )
    return DriftWatchConfig(targets=[target], interval_seconds=interval)


def _summary(drift: int = 0, errors: int = 0) -> RunSummary:
    return RunSummary(results=[], drift_count=drift, error_count=errors)


@pytest.fixture()
def no_sleep():
    """Replace time.sleep with a no-op to keep tests fast."""
    return MagicMock()


# ---------------------------------------------------------------------------
# SchedulerStats
# ---------------------------------------------------------------------------

class TestSchedulerStats:
    def test_initial_state(self):
        stats = SchedulerStats()
        assert stats.total_runs == 0
        assert stats.total_drift == 0
        assert stats.total_errors == 0
        assert stats.last_summary is None

    def test_record_accumulates(self):
        stats = SchedulerStats()
        stats.record(_summary(drift=1, errors=0))
        stats.record(_summary(drift=0, errors=2))
        assert stats.total_runs == 2
        assert stats.total_drift == 1
        assert stats.total_errors == 2

    def test_last_summary_updated(self):
        stats = SchedulerStats()
        s1 = _summary(drift=1)
        s2 = _summary(drift=2)
        stats.record(s1)
        stats.record(s2)
        assert stats.last_summary is s2


# ---------------------------------------------------------------------------
# run_loop
# ---------------------------------------------------------------------------

class TestRunLoop:
    def test_runs_exact_iterations(self, no_sleep):
        config = _make_config()
        with patch("driftwatch.scheduler.run_once", return_value=_summary()) as mock_run:
            stats = run_loop(config, max_iterations=3, _sleep=no_sleep)

        assert mock_run.call_count == 3
        assert stats.total_runs == 3

    def test_sleep_called_between_iterations(self, no_sleep):
        config = _make_config(interval=10.0)
        with patch("driftwatch.scheduler.run_once", return_value=_summary()):
            run_loop(config, max_iterations=3, _sleep=no_sleep)

        # sleep is called *between* iterations: n-1 times for n iterations
        assert no_sleep.call_count == 2
        no_sleep.assert_called_with(10.0)

    def test_interval_override(self, no_sleep):
        config = _make_config(interval=60.0)
        with patch("driftwatch.scheduler.run_once", return_value=_summary()):
            run_loop(config, interval_seconds=5.0, max_iterations=2, _sleep=no_sleep)

        no_sleep.assert_called_with(5.0)

    def test_drift_and_error_totals(self, no_sleep):
        summaries = [_summary(drift=1, errors=0), _summary(drift=0, errors=1)]
        config = _make_config()
        with patch("driftwatch.scheduler.run_once", side_effect=summaries):
            stats = run_loop(config, max_iterations=2, _sleep=no_sleep)

        assert stats.total_drift == 1
        assert stats.total_errors == 1

    def test_single_iteration_no_sleep(self, no_sleep):
        config = _make_config()
        with patch("driftwatch.scheduler.run_once", return_value=_summary()):
            run_loop(config, max_iterations=1, _sleep=no_sleep)

        no_sleep.assert_not_called()
