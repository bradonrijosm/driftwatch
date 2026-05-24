"""Tests for driftwatch.drift_age."""
from __future__ import annotations

import pytest

from driftwatch.drift_age import AgeEntry, DriftAgeTracker, _status_of
from driftwatch.checker import DriftResult
from driftwatch.config import WatchTarget


def _target(name: str = "cfg") -> WatchTarget:
    return WatchTarget(name=name, local_path="/etc/app.conf", remote_url="https://example.com/app.conf")


def _ok(target: WatchTarget) -> DriftResult:
    return DriftResult(target=target, drifted=False, error=None)


def _drift(target: WatchTarget) -> DriftResult:
    return DriftResult(target=target, drifted=True, error=None)


def _error(target: WatchTarget) -> DriftResult:
    return DriftResult(target=target, drifted=False, error="timeout")


# --- _status_of ---

def test_status_ok():
    t = _target()
    assert _status_of(_ok(t)) == "ok"


def test_status_drift():
    t = _target()
    assert _status_of(_drift(t)) == "drift"


def test_status_error():
    t = _target()
    assert _status_of(_error(t)) == "error"


# --- AgeEntry ---

def test_age_entry_age_seconds():
    entry = AgeEntry(status="ok", since=1000.0)
    assert entry.age_seconds(now=1060.0) == pytest.approx(60.0)


# --- DriftAgeTracker ---

def test_first_update_creates_entry():
    tracker = DriftAgeTracker()
    t = _target()
    entry = tracker.update(t, _ok(t), now=100.0)
    assert entry.status == "ok"
    assert entry.since == 100.0
    assert entry.transitions == 0


def test_same_status_does_not_reset_since():
    tracker = DriftAgeTracker()
    t = _target()
    tracker.update(t, _ok(t), now=100.0)
    entry = tracker.update(t, _ok(t), now=200.0)
    assert entry.since == 100.0
    assert entry.transitions == 0


def test_status_change_resets_since_and_increments_transitions():
    tracker = DriftAgeTracker()
    t = _target()
    tracker.update(t, _ok(t), now=100.0)
    entry = tracker.update(t, _drift(t), now=300.0)
    assert entry.status == "drift"
    assert entry.since == 300.0
    assert entry.transitions == 1


def test_multiple_transitions_accumulate():
    tracker = DriftAgeTracker()
    t = _target()
    tracker.update(t, _ok(t), now=100.0)
    tracker.update(t, _drift(t), now=200.0)
    entry = tracker.update(t, _ok(t), now=300.0)
    assert entry.transitions == 2


def test_get_returns_none_for_unknown_target():
    tracker = DriftAgeTracker()
    assert tracker.get(_target()) is None


def test_get_returns_entry_after_update():
    tracker = DriftAgeTracker()
    t = _target()
    tracker.update(t, _ok(t), now=50.0)
    entry = tracker.get(t)
    assert entry is not None
    assert entry.status == "ok"


def test_all_entries_returns_copy():
    tracker = DriftAgeTracker()
    t = _target()
    tracker.update(t, _ok(t), now=1.0)
    entries = tracker.all_entries()
    assert "cfg" in entries
    # mutating the returned dict should not affect tracker
    entries["cfg"] = AgeEntry(status="drift", since=0.0)
    assert tracker.get(t).status == "ok"
