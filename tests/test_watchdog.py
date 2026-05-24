"""Tests for driftwatch.watchdog."""
from __future__ import annotations

import pytest

from driftwatch.config import WatchTarget
from driftwatch.checker import DriftResult
from driftwatch.watchdog import Watchdog, WatchdogConfig


def _target(name: str = "cfg") -> WatchTarget:
    return WatchTarget(name=name, local_path="/etc/app.conf", remote_url="https://example.com/app.conf")


def _result(name: str, status: str) -> DriftResult:
    t = _target(name)
    return DriftResult(target=t, status=status, detail="")


# ---------------------------------------------------------------------------
# WatchdogConfig validation
# ---------------------------------------------------------------------------

class TestWatchdogConfig:
    def test_defaults_are_valid(self):
        cfg = WatchdogConfig()
        assert cfg.failure_threshold >= 1
        assert cfg.recovery_threshold >= 1

    def test_invalid_failure_threshold_raises(self):
        with pytest.raises(ValueError, match="failure_threshold"):
            WatchdogConfig(failure_threshold=0)

    def test_invalid_recovery_threshold_raises(self):
        with pytest.raises(ValueError, match="recovery_threshold"):
            WatchdogConfig(recovery_threshold=0)


# ---------------------------------------------------------------------------
# Watchdog behaviour
# ---------------------------------------------------------------------------

@pytest.fixture()
def dog() -> Watchdog:
    return Watchdog(config=WatchdogConfig(failure_threshold=3, recovery_threshold=2))


def test_new_target_is_healthy(dog):
    assert dog.is_healthy("new") is True


def test_single_failure_does_not_mark_unhealthy(dog):
    dog.record(_result("t", "drift"))
    assert dog.is_healthy("t") is True


def test_threshold_failures_mark_unhealthy(dog):
    for _ in range(3):
        dog.record(_result("t", "drift"))
    assert dog.is_healthy("t") is False


def test_consecutive_failures_counter(dog):
    dog.record(_result("t", "drift"))
    dog.record(_result("t", "drift"))
    assert dog.consecutive_failures("t") == 2


def test_success_resets_failure_counter(dog):
    dog.record(_result("t", "drift"))
    dog.record(_result("t", "ok"))
    assert dog.consecutive_failures("t") == 0


def test_recovery_requires_threshold_successes(dog):
    for _ in range(3):
        dog.record(_result("t", "drift"))
    assert dog.is_healthy("t") is False
    dog.record(_result("t", "ok"))  # only 1 success, threshold=2
    assert dog.is_healthy("t") is False
    dog.record(_result("t", "ok"))  # 2nd success — should recover
    assert dog.is_healthy("t") is True


def test_unhealthy_targets_lists_bad_targets(dog):
    for _ in range(3):
        dog.record(_result("alpha", "error"))
    dog.record(_result("beta", "ok"))
    assert "alpha" in dog.unhealthy_targets()
    assert "beta" not in dog.unhealthy_targets()


def test_reset_removes_state(dog):
    for _ in range(3):
        dog.record(_result("t", "drift"))
    dog.reset("t")
    assert dog.is_healthy("t") is True
    assert dog.consecutive_failures("t") == 0


def test_error_status_counts_as_failure(dog):
    for _ in range(3):
        dog.record(_result("t", "error"))
    assert dog.is_healthy("t") is False
