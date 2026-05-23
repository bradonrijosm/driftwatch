"""Tests for driftwatch.cached_fetcher (retry integration)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.cached_fetcher import CachedFetchResult, fetch_with_cache
from driftwatch.config import WatchTarget
from driftwatch.digest_cache import CacheEntry, DigestCache
from driftwatch.fetcher import FetchResult
from driftwatch.retry import RetryConfig

_NO_RETRY = RetryConfig(max_attempts=1, base_delay=0.0)
_FAST_RETRY = RetryConfig(max_attempts=3, base_delay=0.0)


def _target(name: str = "cfg") -> WatchTarget:
    return WatchTarget(name=name, local_path="/etc/app.conf", remote_url="https://example.com/app.conf")


def _fresh_result(digest: str = "abc123") -> FetchResult:
    return FetchResult(content=b"data", digest=digest, status_code=200, from_cache=False)


# ---------------------------------------------------------------------------
# Cache miss — remote is fetched
# ---------------------------------------------------------------------------

def test_cache_miss_fetches_remote(tmp_path: Path):
    cache = DigestCache(cache_file=tmp_path / "c.json", ttl_seconds=60)
    target = _target()

    with patch("driftwatch.cached_fetcher.fetch_remote", return_value=_fresh_result()) as mock_fetch:
        out = fetch_with_cache(target, cache, retry_cfg=_NO_RETRY)

    mock_fetch.assert_called_once()
    assert out.from_cache is False
    assert out.result.digest == "abc123"


def test_cache_miss_stores_digest(tmp_path: Path):
    cache = DigestCache(cache_file=tmp_path / "c.json", ttl_seconds=60)
    target = _target("svc")

    with patch("driftwatch.cached_fetcher.fetch_remote", return_value=_fresh_result("d1")):
        fetch_with_cache(target, cache, retry_cfg=_NO_RETRY)

    entry = cache.get("svc")
    assert entry is not None
    assert entry.digest == "d1"


# ---------------------------------------------------------------------------
# Cache hit — remote is NOT fetched
# ---------------------------------------------------------------------------

def test_cache_hit_skips_remote(tmp_path: Path):
    cache = DigestCache(cache_file=tmp_path / "c.json", ttl_seconds=300)
    target = _target()
    cache.set(target.name, "stale_digest")

    with patch("driftwatch.cached_fetcher.fetch_remote") as mock_fetch:
        out = fetch_with_cache(target, cache, retry_cfg=_NO_RETRY)

    mock_fetch.assert_not_called()
    assert out.from_cache is True
    assert out.result.status_code == 304


# ---------------------------------------------------------------------------
# Retry behaviour
# ---------------------------------------------------------------------------

def test_retry_succeeds_after_transient_failure(tmp_path: Path):
    import httpx

    cache = DigestCache(cache_file=tmp_path / "c.json", ttl_seconds=60)
    target = _target()
    call_count = 0

    def flaky_fetch(t, *, client=None):  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.ConnectError("transient")
        return _fresh_result("ok_digest")

    with patch("driftwatch.cached_fetcher.fetch_remote", side_effect=flaky_fetch):
        out = fetch_with_cache(target, cache, retry_cfg=_FAST_RETRY)

    assert call_count == 3
    assert out.result.digest == "ok_digest"
    assert out.from_cache is False


def test_retry_exhausted_raises(tmp_path: Path):
    import httpx

    cache = DigestCache(cache_file=tmp_path / "c.json", ttl_seconds=60)
    target = _target()

    with patch(
        "driftwatch.cached_fetcher.fetch_remote",
        side_effect=httpx.ConnectError("always down"),
    ):
        with pytest.raises(httpx.ConnectError):
            fetch_with_cache(target, cache, retry_cfg=_FAST_RETRY)
