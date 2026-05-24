"""Tests for driftwatch.circuit_breaker."""
import time
import pytest

from driftwatch.circuit_breaker import (
    BreakerState,
    CircuitBreaker,
    CircuitBreakerConfig,
)


class TestCircuitBreakerConfig:
    def test_defaults_are_valid(self):
        cfg = CircuitBreakerConfig()
        assert cfg.failure_threshold >= 1
        assert cfg.recovery_timeout > 0
        assert cfg.success_threshold >= 1

    def test_invalid_failure_threshold_raises(self):
        with pytest.raises(ValueError, match="failure_threshold"):
            CircuitBreakerConfig(failure_threshold=0)

    def test_invalid_recovery_timeout_raises(self):
        with pytest.raises(ValueError, match="recovery_timeout"):
            CircuitBreakerConfig(recovery_timeout=0)

    def test_invalid_success_threshold_raises(self):
        with pytest.raises(ValueError, match="success_threshold"):
            CircuitBreakerConfig(success_threshold=0)


@pytest.fixture()
def cb():
    return CircuitBreaker(CircuitBreakerConfig(failure_threshold=2, recovery_timeout=30.0))


def test_new_target_is_allowed(cb):
    assert cb.is_allowed("svc-a") is True


def test_state_starts_closed(cb):
    assert cb.state("svc-a") == BreakerState.CLOSED


def test_opens_after_threshold_failures(cb):
    cb.record_failure("svc-a")
    assert cb.state("svc-a") == BreakerState.CLOSED
    cb.record_failure("svc-a")
    assert cb.state("svc-a") == BreakerState.OPEN


def test_open_breaker_blocks_requests(cb):
    cb.record_failure("svc-a")
    cb.record_failure("svc-a")
    assert cb.is_allowed("svc-a") is False


def test_success_resets_failure_count(cb):
    cb.record_failure("svc-a")
    cb.record_success("svc-a")
    cb.record_failure("svc-a")
    # only 1 consecutive failure after success — still closed
    assert cb.state("svc-a") == BreakerState.CLOSED


def test_transitions_to_half_open_after_timeout(cb, monkeypatch):
    cb.record_failure("svc-a")
    cb.record_failure("svc-a")
    assert cb.state("svc-a") == BreakerState.OPEN

    # advance monotonic clock past recovery_timeout
    original = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: original() + 31.0)

    assert cb.is_allowed("svc-a") is True
    assert cb.state("svc-a") == BreakerState.HALF_OPEN


def test_half_open_closes_on_success(cb, monkeypatch):
    cb.record_failure("svc-a")
    cb.record_failure("svc-a")
    original = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: original() + 31.0)
    cb.is_allowed("svc-a")  # triggers HALF_OPEN transition
    cb.record_success("svc-a")
    assert cb.state("svc-a") == BreakerState.CLOSED


def test_half_open_reopens_on_failure(cb, monkeypatch):
    cb.record_failure("svc-a")
    cb.record_failure("svc-a")
    original = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: original() + 31.0)
    cb.is_allowed("svc-a")
    cb.record_failure("svc-a")
    assert cb.state("svc-a") == BreakerState.OPEN


def test_reset_clears_state(cb):
    cb.record_failure("svc-a")
    cb.record_failure("svc-a")
    cb.reset("svc-a")
    assert cb.state("svc-a") == BreakerState.CLOSED
    assert cb.is_allowed("svc-a") is True


def test_independent_targets(cb):
    cb.record_failure("svc-a")
    cb.record_failure("svc-a")
    assert cb.state("svc-a") == BreakerState.OPEN
    assert cb.state("svc-b") == BreakerState.CLOSED
