"""Tests for driftwatch.target_status."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from driftwatch.checker import DriftResult
from driftwatch.config import WatchTarget
from driftwatch.runner import RunSummary
from driftwatch.target_status import (
    TargetStatus,
    build_status_map,
)


def _make_target(path: str) -> WatchTarget:
    return WatchTarget(local_path=path, remote_url="https://example.com/cfg")


def _clean_result() -> DriftResult:
    return DriftResult(
        drifted=False, local_checksum="abc", remote_checksum="abc", error=None
    )


def _drift_result() -> DriftResult:
    return DriftResult(
        drifted=True, local_checksum="aaa", remote_checksum="bbb", error=None
    )


def _error_result() -> DriftResult:
    return DriftResult(
        drifted=False, local_checksum=None, remote_checksum=None,
        error="file not found"
    )


def _summary(targets, results) -> RunSummary:
    cfg = MagicMock()
    cfg.targets = targets
    s = RunSummary(config=cfg, targets=targets, results=results)
    return s


def test_clean_target_is_clean():
    t = _make_target("/etc/app.conf")
    sm = build_status_map(_summary([t], [_clean_result()]))
    entry = sm.get("/etc/app.conf")
    assert entry is not None
    assert entry.status == TargetStatus.CLEAN
    assert entry.detail == ""


def test_drifted_target_is_drifted():
    t = _make_target("/etc/app.conf")
    sm = build_status_map(_summary([t], [_drift_result()]))
    entry = sm.get("/etc/app.conf")
    assert entry.status == TargetStatus.DRIFTED
    assert "aaa" in entry.detail
    assert "bbb" in entry.detail


def test_error_target_is_error():
    t = _make_target("/etc/app.conf")
    sm = build_status_map(_summary([t], [_error_result()]))
    entry = sm.get("/etc/app.conf")
    assert entry.status == TargetStatus.ERROR
    assert "file not found" in entry.detail


def test_all_clean_true_when_all_clean():
    targets = [_make_target(f"/etc/{i}.conf") for i in range(3)]
    results = [_clean_result() for _ in targets]
    sm = build_status_map(_summary(targets, results))
    assert sm.all_clean() is True


def test_all_clean_false_when_any_drift():
    t1 = _make_target("/a")
    t2 = _make_target("/b")
    sm = build_status_map(_summary([t1, t2], [_clean_result(), _drift_result()]))
    assert sm.all_clean() is False


def test_by_status_filters_correctly():
    t1 = _make_target("/a")
    t2 = _make_target("/b")
    t3 = _make_target("/c")
    sm = build_status_map(
        _summary([t1, t2, t3], [_clean_result(), _drift_result(), _error_result()])
    )
    assert len(sm.by_status(TargetStatus.CLEAN)) == 1
    assert len(sm.by_status(TargetStatus.DRIFTED)) == 1
    assert len(sm.by_status(TargetStatus.ERROR)) == 1


def test_unknown_path_returns_none():
    sm = build_status_map(_summary([], []))
    assert sm.get("/nonexistent") is None
