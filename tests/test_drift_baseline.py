"""Tests for driftwatch.drift_baseline."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from driftwatch.drift_baseline import BaselineEntry, BaselineStore


# ---------------------------------------------------------------------------
# BaselineEntry
# ---------------------------------------------------------------------------

class TestBaselineEntry:
    def test_age_seconds_uses_captured_at(self):
        now = time.time()
        entry = BaselineEntry(url="http://x", digest="abc", captured_at=now - 60)
        assert 59 < entry.age_seconds(now=now) < 61

    def test_age_seconds_defaults_to_current_time(self):
        entry = BaselineEntry(url="http://x", digest="abc", captured_at=time.time() - 5)
        assert entry.age_seconds() >= 4

    def test_round_trip_dict(self):
        entry = BaselineEntry(url="http://example.com", digest="deadbeef", captured_at=1_700_000_000.0)
        restored = BaselineEntry.from_dict(entry.as_dict())
        assert restored.url == entry.url
        assert restored.digest == entry.digest
        assert restored.captured_at == entry.captured_at


# ---------------------------------------------------------------------------
# BaselineStore fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path: Path) -> BaselineStore:
    return BaselineStore(_path=tmp_path / "baseline.json")


# ---------------------------------------------------------------------------
# BaselineStore tests
# ---------------------------------------------------------------------------

def test_empty_store_has_no_entries(store: BaselineStore):
    assert len(store) == 0


def test_get_missing_returns_none(store: BaselineStore):
    assert store.get("http://missing") is None


def test_set_stores_and_returns_entry(store: BaselineStore):
    entry = store.set("http://example.com", "abc123")
    assert entry.url == "http://example.com"
    assert entry.digest == "abc123"
    assert store.get("http://example.com") is entry


def test_set_accepts_explicit_timestamp(store: BaselineStore):
    ts = 1_700_000_000.0
    entry = store.set("http://example.com", "abc", now=ts)
    assert entry.captured_at == ts


def test_set_persists_to_disk(tmp_path: Path):
    path = tmp_path / "baseline.json"
    s1 = BaselineStore(_path=path)
    s1.set("http://example.com", "digest1", now=1_700_000_000.0)

    s2 = BaselineStore(_path=path)
    entry = s2.get("http://example.com")
    assert entry is not None
    assert entry.digest == "digest1"


def test_remove_deletes_entry(store: BaselineStore):
    store.set("http://a.com", "d1")
    removed = store.remove("http://a.com")
    assert removed is True
    assert store.get("http://a.com") is None


def test_remove_missing_returns_false(store: BaselineStore):
    assert store.remove("http://not-there.com") is False


def test_all_entries_returns_copy(store: BaselineStore):
    store.set("http://a.com", "d1")
    store.set("http://b.com", "d2")
    entries = store.all_entries()
    assert len(entries) == 2
    # Mutating the returned dict should not affect the store
    entries.clear()
    assert len(store) == 2


def test_corrupted_file_loads_empty(tmp_path: Path):
    path = tmp_path / "baseline.json"
    path.write_text("not valid json")
    store = BaselineStore(_path=path)
    assert len(store) == 0
