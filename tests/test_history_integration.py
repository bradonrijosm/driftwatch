"""Integration test: runner -> history -> report pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.history import HistoryStore, record_run_summary
from driftwatch.history_report import build_history_report


def _make_result(name: str, drifted: bool = False, error: str | None = None) -> MagicMock:
    target = MagicMock()
    target.name = name
    target.local_path = f"/etc/{name}.conf"
    target.remote_url = f"https://example.com/{name}.conf"
    result = MagicMock()
    result.target = target
    result.drifted = drifted
    result.error = error
    return result


def _make_summary(*results: MagicMock) -> MagicMock:
    summary = MagicMock()
    summary.results = list(results)
    return summary


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:  # type: ignore[misc]
    s = HistoryStore(db_path=tmp_path / "int.db")
    yield s
    s.close()


def test_full_pipeline_clean(store: HistoryStore) -> None:
    summary = _make_summary(_make_result("a"), _make_result("b"))
    record_run_summary(store, summary, ts=1_700_000_000.0)

    report = build_history_report(store.recent())
    assert "ok: 2" in report
    assert "drift: 0" in report


def test_full_pipeline_mixed(store: HistoryStore) -> None:
    summary = _make_summary(
        _make_result("alpha"),
        _make_result("beta", drifted=True),
        _make_result("gamma", error="timeout"),
    )
    record_run_summary(store, summary, ts=1_700_000_000.0)

    events = store.recent()
    report = build_history_report(events)

    assert "ok: 1" in report
    assert "drift: 1" in report
    assert "error: 1" in report
    assert "timeout" in report


def test_multiple_runs_accumulate(store: HistoryStore) -> None:
    for i in range(3):
        summary = _make_summary(_make_result(f"t{i}"))
        record_run_summary(store, summary, ts=1_700_000_000.0 + i)

    assert len(store.recent(limit=100)) == 3


def test_report_ordering_newest_first(store: HistoryStore) -> None:
    record_run_summary(store, _make_summary(_make_result("old")), ts=1_700_000_000.0)
    record_run_summary(store, _make_summary(_make_result("new")), ts=1_700_001_000.0)

    events = store.recent(limit=2)
    assert events[0].target_name == "new"
    assert events[1].target_name == "old"
