"""Tests for driftwatch.digest_cache."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from driftwatch.digest_cache import CacheEntry, DigestCache

URL = "https://example.com/config.toml"
SUM = "abc123"


@pytest.fixture()
def cache_file(tmp_path: Path) -> Path:
    return tmp_path / "digests.json"


@pytest.fixture()
def cache(cache_file: Path) -> DigestCache:
    return DigestCache(cache_path=cache_file, ttl=60)


class TestCacheEntry:
    def test_fresh_entry_is_fresh(self) -> None:
        entry = CacheEntry(checksum=SUM, fetched_at=time.time(), url=URL)
        assert entry.is_fresh(ttl=60) is True

    def test_stale_entry_is_not_fresh(self) -> None:
        entry = CacheEntry(checksum=SUM, fetched_at=time.time() - 120, url=URL)
        assert entry.is_fresh(ttl=60) is False


class TestDigestCache:
    def test_get_returns_none_when_empty(self, cache: DigestCache) -> None:
        assert cache.get(URL) is None

    def test_put_and_get_returns_entry(self, cache: DigestCache) -> None:
        cache.put(URL, SUM)
        entry = cache.get(URL)
        assert entry is not None
        assert entry.checksum == SUM
        assert entry.url == URL

    def test_put_persists_to_disk(self, cache: DigestCache, cache_file: Path) -> None:
        cache.put(URL, SUM)
        assert cache_file.exists()
        raw = json.loads(cache_file.read_text())
        assert URL in raw
        assert raw[URL]["checksum"] == SUM

    def test_cache_loaded_from_disk(self, cache_file: Path) -> None:
        first = DigestCache(cache_path=cache_file, ttl=60)
        first.put(URL, SUM)

        second = DigestCache(cache_path=cache_file, ttl=60)
        entry = second.get(URL)
        assert entry is not None
        assert entry.checksum == SUM

    def test_stale_entry_returns_none(self, cache_file: Path) -> None:
        cache = DigestCache(cache_path=cache_file, ttl=1)
        cache.put(URL, SUM)
        # Manually backdate the entry
        cache._entries[URL].fetched_at = time.time() - 10
        assert cache.get(URL) is None

    def test_invalidate_removes_entry(self, cache: DigestCache) -> None:
        cache.put(URL, SUM)
        cache.invalidate(URL)
        assert cache.get(URL) is None

    def test_len_reflects_entry_count(self, cache: DigestCache) -> None:
        assert len(cache) == 0
        cache.put(URL, SUM)
        cache.put(URL + "/other", "def456")
        assert len(cache) == 2

    def test_corrupt_cache_file_loads_empty(self, cache_file: Path) -> None:
        cache_file.write_text("not valid json{{")
        cache = DigestCache(cache_path=cache_file, ttl=60)
        assert len(cache) == 0
