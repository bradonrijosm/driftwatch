"""Tests for driftwatch.rate_limiter."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from driftwatch.rate_limiter import RateLimiter, RateLimiterConfig


# ---------------------------------------------------------------------------
# RateLimiterConfig validation
# ---------------------------------------------------------------------------

class TestRateLimiterConfig:
    def test_defaults_are_positive(self):
        cfg = RateLimiterConfig()
        assert cfg.max_tokens > 0
        assert cfg.refill_rate > 0

    def test_invalid_max_tokens_raises(self):
        with pytest.raises(ValueError, match="max_tokens"):
            RateLimiterConfig(max_tokens=0)

    def test_invalid_refill_rate_raises(self):
        with pytest.raises(ValueError, match="refill_rate"):
            RateLimiterConfig(refill_rate=-1.0)


# ---------------------------------------------------------------------------
# RateLimiter behaviour
# ---------------------------------------------------------------------------

@pytest.fixture()
def limiter():
    cfg = RateLimiterConfig(max_tokens=3.0, refill_rate=1.0)
    return RateLimiter(config=cfg)


def test_initial_acquire_succeeds(limiter):
    assert limiter.acquire() is True


def test_burst_capacity_exhausted(limiter):
    for _ in range(3):
        limiter.acquire()
    assert limiter.acquire() is False


def test_rejected_count_increments(limiter):
    for _ in range(3):
        limiter.acquire()
    limiter.acquire()  # rejected
    limiter.acquire()  # rejected
    assert limiter.rejected_count == 2


def test_tokens_refill_over_time(limiter):
    for _ in range(3):
        limiter.acquire()
    assert limiter.acquire() is False

    # Simulate 2 seconds passing so 2 tokens are refilled
    future = time.monotonic() + 2.0
    with patch("driftwatch.rate_limiter.time.monotonic", return_value=future):
        assert limiter.acquire() is True
        assert limiter.acquire() is True
        assert limiter.acquire() is False


def test_tokens_capped_at_max(limiter):
    future = time.monotonic() + 1000.0
    with patch("driftwatch.rate_limiter.time.monotonic", return_value=future):
        assert limiter.available_tokens == limiter.config.max_tokens


def test_reset_restores_full_capacity(limiter):
    for _ in range(3):
        limiter.acquire()
    limiter.reset()
    assert limiter.acquire() is True
    assert limiter.rejected_count == 0


def test_acquire_zero_tokens_raises(limiter):
    with pytest.raises(ValueError, match="tokens"):
        limiter.acquire(0)


def test_acquire_fractional_tokens(limiter):
    # 3 tokens available; consuming 1.5 twice should succeed, third fails
    assert limiter.acquire(1.5) is True
    assert limiter.acquire(1.5) is True
    assert limiter.acquire(1.5) is False
