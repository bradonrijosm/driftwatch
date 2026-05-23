"""Fetch remote content with digest caching and optional retry."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

from driftwatch.config import WatchTarget
from driftwatch.digest_cache import DigestCache
from driftwatch.fetcher import FetchError, FetchResult, fetch_remote
from driftwatch.retry import RetryConfig, with_retry

log = logging.getLogger(__name__)

_DEFAULT_RETRY = RetryConfig(max_attempts=3, base_delay=0.5, backoff_factor=2.0)


@dataclass(frozen=True)
class CachedFetchResult:
    result: FetchResult
    from_cache: bool


def make_cache(cache_dir: Path, ttl_seconds: int = 300) -> DigestCache:
    return DigestCache(cache_file=cache_dir / "digest_cache.json", ttl_seconds=ttl_seconds)


def fetch_with_cache(
    target: WatchTarget,
    cache: DigestCache,
    *,
    client: httpx.Client | None = None,
    retry_cfg: RetryConfig = _DEFAULT_RETRY,
) -> CachedFetchResult:
    """Fetch *target* using the digest cache to skip unchanged remote content.

    Retries transient HTTP / connection errors according to *retry_cfg*.
    Returns a :class:`CachedFetchResult` indicating whether the cache was hit.
    """
    cached = cache.get(target.name)
    if cached is not None and cached.is_fresh():
        log.debug("cache hit for %s (digest=%s)", target.name, cached.digest[:8])
        result = FetchResult(content=b"", digest=cached.digest, status_code=304, from_cache=True)
        return CachedFetchResult(result=result, from_cache=True)

    def _do_fetch() -> FetchResult:
        return fetch_remote(target, client=client)

    fetch_result, stats = with_retry(
        _do_fetch,
        retry_cfg,
        retryable=(httpx.HTTPError, FetchError),
    )

    if stats.attempts > 1:
        log.info("fetched %s after %d attempts", target.name, stats.attempts)

    cache.set(target.name, fetch_result.digest)
    return CachedFetchResult(result=fetch_result, from_cache=False)
