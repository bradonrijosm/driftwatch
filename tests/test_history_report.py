"""Tests for driftwatch.history_report."""

from __future__ import annotations

import time
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from driftwatch.history import DriftEvent, HistoryStore
from driftwatch.history_report import build_history_report, print_history_report


def _ev(status: str, name: str = "cfg", detail: str | None = None) -> DriftEvent:
    return DriftEvent(
        target_name=name,
        local_path="/etc/app.conf",
        remote_url="https://example.com/app.conf",
        status=status,
        detail=detail,
        checked_at=1_700_000_000.0,
    )


# ---------------------------------------------------------------------------
# build_history_report
# ---------------------------------------------------------------------------


def test_empty_events_returns_placeholder() -> None:
    report = build_history_report([])
    assert "No history" in report


def test_header_contains_counts() -> None:
    events = [_ev("ok"), _ev("drift"), _ev("error")]
    report = build_history_report(events)
    assert "drift: 1" in report
    assert "error: 1" in report
    assert "ok: 1" in report


def test_ok_icon_present() -> None:
    report = build_history_report([_ev("ok")])
    assert "\u2705" in report


def test_drift_icon_present() -> None:
    report = build_history_report([_ev("drift")])
    assert "\u26a0" in report


def test_error_icon_present() -> None:
    report = build_history_report([_ev("error")])
    assert "\u274c" in report


def test_detail_included_when_present() -> None:
    report = build_history_report([_ev("drift", detail="checksums differ")])
    assert "checksums differ" in report


def test_detail_absent_when_none() -> None:
    report = build_history_report([_ev("ok")])
    assert "detail:" not in report


def test_target_name_in_report() -> None:
    report = build_history_report([_ev("ok", name="nginx-conf")])
    assert "nginx-conf" in report


def test_timestamp_formatted() -> None:
    report = build_history_report([_ev("ok")])
    assert "2023-11-14" in report  # 1_700_000_000 is 2023-11-14 UTC


# ---------------------------------------------------------------------------
# print_history_report
# ---------------------------------------------------------------------------


def test_print_history_report_uses_store(tmp_path: Path) -> None:
    db = tmp_path / "h.db"
    store = HistoryStore(db_path=db)
    store.record(_ev("drift"))

    with patch("builtins.print") as mock_print:
        print_history_report(store, limit=10)
        printed = mock_print.call_args[0][0]

    assert "drift: 1" in printed
    store.close()
