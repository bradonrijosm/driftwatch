"""Token-bucket rate limiter for outbound webhook notifications."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class RateLimiterConfig:
    """Configuration for the token-bucket rate limiter."""

    max_tokens: float = 10.0      # burst capacity
    refill_rate: float = 1.0      # tokens added per second

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be > 0")
        if self.refill_rate <= 0:
            raise ValueError("refill_rate must be > 0")


@dataclass
class RateLimiter:
    """Thread-safe token-bucket rate limiter."""

    config: RateLimiterConfig = field(default_factory=RateLimiterConfig)
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)
    _lock: Lock = field(init=False, repr=False)
    _rejected: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self._tokens = self.config.max_tokens
        self._last_refill = time.monotonic()
        self._lock = Lock()

    def _refill(self, now: float) -> None:
        elapsed = now - self._last_refill
        gained = elapsed * self.config.refill_rate
        self._tokens = min(self.config.max_tokens, self._tokens + gained)
        self._last_refill = now

    def acquire(self, tokens: float = 1.0) -> bool:
        """Attempt to consume *tokens* from the bucket.

        Returns True if the request is allowed, False if rate-limited.
        """
        if tokens <= 0:
            raise ValueError("tokens must be > 0")
        with self._lock:
            self._refill(time.monotonic())
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            self._rejected += 1
            return False

    @property
    def available_tokens(self) -> float:
        with self._lock:
            self._refill(time.monotonic())
            return self._tokens

    @property
    def rejected_count(self) -> int:
        with self._lock:
            return self._rejected

    def reset(self) -> None:
        """Restore bucket to full capacity (useful for testing)."""
        with self._lock:
            self._tokens = self.config.max_tokens
            self._last_refill = time.monotonic()
            self._rejected = 0
