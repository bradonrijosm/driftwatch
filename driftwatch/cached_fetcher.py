"""Fetcher wrapper that uses DigestCache to skip unchanged remote content."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from driftwatch.digest_cache import DigestCache
from driftwatch.fetcher import FetchError, FetchResult, fetch_remote

log = logging.getLogger(__name__)


@dataclass
class CachedFetchResult:
    result: FetchResult
    cache_hit: bool


def make_cache(cache_dir: Path, ttl: int = 300) -> DigestCache:
    """Convenience factory used by the runner."""
    return DigestCache(cache_path=cache_dir / "digests.json", ttl=ttl)


def fetch_with_cache(
    url: str,
    cache: DigestCache,
    *,
    timeout: int = 10,
) -> CachedFetchResult:
    """Fetch *url*, returning a cached checksum when the content is unchanged.

    If the cache has a fresh entry whose checksum matches the newly fetched
    content the caller can skip re-running the diff against the local file.
    The cache is always updated with the latest checksum on a successful fetch.
    """
    try:
        result = fetch_remote(url, timeout=timeout)
    except FetchError:
        raise

    cached = cache.get(url)
    cache_hit = cached is not None and cached.checksum == result.checksum

    if cache_hit:
        log.debug("Cache hit for %s (checksum %s)", url, result.checksum)
    else:
        log.debug("Cache miss for %s — storing checksum %s", url, result.checksum)
        cache.put(url, result.checksum)

    return CachedFetchResult(result=result, cache_hit=cache_hit)
