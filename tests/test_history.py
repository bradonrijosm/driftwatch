"""Tests for driftwatch.history."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from driftwatch.history import DriftEvent, HistoryStore, record_run_summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:  # type: ignore[misc]
    db = tmp_path / "test_history.db"
    s = HistoryStore(db_path=db)
    yield s
    s.close()


def _event(
    name: str = "cfg",
    status: str = "ok",
    detail: str | None = None,
    ts: float | None = None,
) -> DriftEvent:
    return DriftEvent(
        target_name=name,
        local_path="/etc/app.conf",
        remote_url="https://example.com/app.conf",
        status=status,
        detail=detail,
        checked_at=ts or time.time(),
    )


# ---------------------------------------------------------------------------
# HistoryStore.record
# ---------------------------------------------------------------------------


def test_record_returns_incrementing_ids(store: HistoryStore) -> None:
    id1 = store.record(_event())
    id2 = store.record(_event())
    assert id1 == 1
    assert id2 == 2


def test_record_persists_status(store: HistoryStore) -> None:
    store.record(_event(status="drift", detail="checksums differ"))
    events = store.recent()
    assert len(events) == 1
    assert events[0].status == "drift"
    assert events[0].detail == "checksums differ"


# ---------------------------------------------------------------------------
# HistoryStore.recent
# ---------------------------------------------------------------------------


def test_recent_returns_newest_first(store: HistoryStore) -> None:
    base = 1_700_000_000.0
    for i in range(5):
        store.record(_event(name=f"t{i}", ts=base + i))
    events = store.recent(limit=5)
    assert events[0].target_name == "t4"
    assert events[-1].target_name == "t0"


def test_recent_respects_limit(store: HistoryStore) -> None:
    for _ in range(10):
        store.record(_event())
    assert len(store.recent(limit=3)) == 3


def test_recent_empty_db(store: HistoryStore) -> None:
    assert store.recent() == []


# ---------------------------------------------------------------------------
# record_run_summary
# ---------------------------------------------------------------------------


def _make_result(name: str, drifted: bool = False, error: str | None = None) -> MagicMock:
    target = MagicMock()
    target.name = name
    target.local_path = "/etc/app.conf"
    target.remote_url = "https://example.com/app.conf"
    result = MagicMock()
    result.target = target
    result.drifted = drifted
    result.error = error
    return result


def test_record_run_summary_ok(store: HistoryStore) -> None:
    summary = MagicMock()
    summary.results = [_make_result("a"), _make_result("b")]
    record_run_summary(store, summary, ts=1_700_000_000.0)
    events = store.recent()
    assert len(events) == 2
    assert all(e.status == "ok" for e in events)


def test_record_run_summary_drift(store: HistoryStore) -> None:
    summary = MagicMock()
    summary.results = [_make_result("x", drifted=True)]
    record_run_summary(store, summary)
    assert store.recent()[0].status == "drift"


def test_record_run_summary_error(store: HistoryStore) -> None:
    summary = MagicMock()
    summary.results = [_make_result("y", error="connection refused")]
    record_run_summary(store, summary)
    ev = store.recent()[0]
    assert ev.status == "error"
    assert ev.detail == "connection refused"
