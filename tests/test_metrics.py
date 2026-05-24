"""Tests for driftwatch.metrics."""
from __future__ import annotations

import threading

import pytest

from driftwatch.metrics import (
    MetricsCollector,
    MetricsSnapshot,
    increment,
    reset_all,
    snapshot,
)


# ---------------------------------------------------------------------------
# MetricsSnapshot
# ---------------------------------------------------------------------------


class TestMetricsSnapshot:
    def test_get_existing_key(self):
        s = MetricsSnapshot({"checks_run": 5})
        assert s.get("checks_run") == 5

    def test_get_missing_key_returns_default(self):
        s = MetricsSnapshot({})
        assert s.get("missing") == 0

    def test_get_missing_key_custom_default(self):
        s = MetricsSnapshot({})
        assert s.get("missing", 99) == 99


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------


@pytest.fixture()
def collector() -> MetricsCollector:
    return MetricsCollector()


def test_initial_counter_is_zero(collector):
    assert collector.get("anything") == 0


def test_increment_default_amount(collector):
    collector.increment("checks_run")
    assert collector.get("checks_run") == 1


def test_increment_custom_amount(collector):
    collector.increment("drift_detected", 3)
    assert collector.get("drift_detected") == 3


def test_increment_accumulates(collector):
    for _ in range(5):
        collector.increment("errors")
    assert collector.get("errors") == 5


def test_increment_negative_raises(collector):
    with pytest.raises(ValueError, match="amount must be >= 0"):
        collector.increment("bad", -1)


def test_reset_single_counter(collector):
    collector.increment("checks_run", 10)
    collector.reset("checks_run")
    assert collector.get("checks_run") == 0


def test_reset_all_clears_everything(collector):
    collector.increment("a", 1)
    collector.increment("b", 2)
    collector.reset_all()
    snap = collector.snapshot()
    assert snap.counters == {}


def test_snapshot_is_independent_copy(collector):
    collector.increment("x", 7)
    snap = collector.snapshot()
    collector.increment("x", 3)  # mutate after snapshot
    assert snap.get("x") == 7  # snapshot unchanged


def test_thread_safety(collector):
    """Concurrent increments should not lose updates."""
    threads = [
        threading.Thread(target=collector.increment, args=("t", 1))
        for _ in range(200)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert collector.get("t") == 200


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_default():
    """Ensure the default collector is clean before each test."""
    reset_all()
    yield
    reset_all()


def test_module_increment_and_snapshot():
    increment("checks_run", 2)
    snap = snapshot()
    assert snap.get("checks_run") == 2


def test_module_reset_all():
    increment("drift_detected", 5)
    reset_all()
    assert snapshot().get("drift_detected") == 0
