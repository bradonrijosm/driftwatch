"""Retry logic for transient fetch failures."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behaviour."""

    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    backoff_factor: float = 2.0
    max_delay: float = 30.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be >= 0")
        if self.backoff_factor < 1:
            raise ValueError("backoff_factor must be >= 1")

    def delay_for(self, attempt: int) -> float:
        """Return sleep duration (seconds) before *attempt* (0-indexed)."""
        if attempt == 0:
            return 0.0
        raw = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(raw, self.max_delay)


@dataclass
class RetryStats:
    attempts: int = 0
    total_delay: float = 0.0
    succeeded: bool = False
    errors: list[Exception] = field(default_factory=list)


def with_retry(
    fn: Callable[[], T],
    cfg: RetryConfig,
    *,
    retryable: type[Exception] | tuple[type[Exception], ...] = Exception,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[T, RetryStats]:
    """Call *fn* up to *cfg.max_attempts* times, retrying on *retryable* exceptions.

    Returns ``(result, stats)`` on success; re-raises the last exception on
    exhaustion.
    """
    stats = RetryStats()
    last_exc: Exception | None = None

    for attempt in range(cfg.max_attempts):
        delay = cfg.delay_for(attempt)
        if delay > 0:
            log.debug("retry attempt %d/%d — sleeping %.1fs", attempt + 1, cfg.max_attempts, delay)
            sleep_fn(delay)
            stats.total_delay += delay

        stats.attempts += 1
        try:
            result = fn()
            stats.succeeded = True
            return result, stats
        except retryable as exc:  # type: ignore[misc]
            last_exc = exc
            stats.errors.append(exc)
            log.warning("attempt %d failed: %s", attempt + 1, exc)

    assert last_exc is not None
    raise last_exc
