"""Tests for driftwatch.retry."""
from __future__ import annotations

import pytest

from driftwatch.retry import RetryConfig, RetryStats, with_retry


# ---------------------------------------------------------------------------
# RetryConfig
# ---------------------------------------------------------------------------

class TestRetryConfig:
    def test_default_values(self):
        cfg = RetryConfig()
        assert cfg.max_attempts == 3
        assert cfg.base_delay == 1.0
        assert cfg.backoff_factor == 2.0
        assert cfg.max_delay == 30.0

    def test_invalid_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RetryConfig(max_attempts=0)

    def test_invalid_base_delay_raises(self):
        with pytest.raises(ValueError, match="base_delay"):
            RetryConfig(base_delay=-0.1)

    def test_invalid_backoff_factor_raises(self):
        with pytest.raises(ValueError, match="backoff_factor"):
            RetryConfig(backoff_factor=0.5)

    def test_delay_for_first_attempt_is_zero(self):
        cfg = RetryConfig(base_delay=2.0, backoff_factor=2.0)
        assert cfg.delay_for(0) == 0.0

    def test_delay_increases_with_backoff(self):
        cfg = RetryConfig(base_delay=1.0, backoff_factor=2.0, max_delay=100.0)
        assert cfg.delay_for(1) == 1.0
        assert cfg.delay_for(2) == 2.0
        assert cfg.delay_for(3) == 4.0

    def test_delay_capped_at_max_delay(self):
        cfg = RetryConfig(base_delay=10.0, backoff_factor=10.0, max_delay=15.0)
        assert cfg.delay_for(2) == 15.0


# ---------------------------------------------------------------------------
# with_retry
# ---------------------------------------------------------------------------

def _no_sleep(seconds: float) -> None:  # noqa: ARG001
    pass


def test_success_on_first_attempt():
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    result, stats = with_retry(fn, RetryConfig(max_attempts=3), sleep_fn=_no_sleep)
    assert result == "ok"
    assert stats.attempts == 1
    assert stats.succeeded is True
    assert stats.errors == []
    assert stats.total_delay == 0.0


def test_success_after_transient_failures():
    attempt_count = 0

    def fn():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError("transient")
        return "recovered"

    cfg = RetryConfig(max_attempts=3, base_delay=0.0)
    result, stats = with_retry(fn, cfg, retryable=ConnectionError, sleep_fn=_no_sleep)
    assert result == "recovered"
    assert stats.attempts == 3
    assert len(stats.errors) == 2
    assert stats.succeeded is True


def test_raises_after_max_attempts_exhausted():
    def fn():
        raise TimeoutError("always fails")

    cfg = RetryConfig(max_attempts=3, base_delay=0.0)
    with pytest.raises(TimeoutError, match="always fails"):
        with_retry(fn, cfg, retryable=TimeoutError, sleep_fn=_no_sleep)


def test_stats_record_all_errors():
    def fn():
        raise OSError("boom")

    cfg = RetryConfig(max_attempts=4, base_delay=0.0)
    with pytest.raises(OSError):
        with_retry(fn, cfg, sleep_fn=_no_sleep)


def test_non_retryable_exception_propagates_immediately():
    calls = 0

    def fn():
        nonlocal calls
        calls += 1
        raise ValueError("not retryable")

    cfg = RetryConfig(max_attempts=5, base_delay=0.0)
    with pytest.raises(ValueError):
        with_retry(fn, cfg, retryable=ConnectionError, sleep_fn=_no_sleep)
    assert calls == 1


def test_sleep_called_with_correct_delays():
    slept: list[float] = []
    attempt_count = 0

    def fn():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError("retry me")
        return "done"

    cfg = RetryConfig(max_attempts=3, base_delay=1.0, backoff_factor=2.0)
    with_retry(fn, cfg, retryable=ConnectionError, sleep_fn=slept.append)
    assert slept == [1.0, 2.0]
