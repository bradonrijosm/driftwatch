"""Tests for driftwatch.alert_filter."""
from __future__ import annotations

import pytest

from driftwatch.alert_filter import AlertFilter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

T0 = 1_000.0  # arbitrary monotonic baseline


# ---------------------------------------------------------------------------
# First-alert behaviour
# ---------------------------------------------------------------------------


def test_first_alert_always_fires():
    f = AlertFilter(cooldown_seconds=60)
    assert f.should_alert("svc/nginx.conf", _now=T0) is True


def test_alert_count_is_one_after_first_alert():
    f = AlertFilter(cooldown_seconds=60)
    f.should_alert("svc/nginx.conf", _now=T0)
    assert f.alert_count("svc/nginx.conf") == 1


def test_unknown_target_has_zero_alert_count():
    f = AlertFilter(cooldown_seconds=60)
    assert f.alert_count("nope") == 0


# ---------------------------------------------------------------------------
# Suppression within cooldown window
# ---------------------------------------------------------------------------


def test_second_alert_suppressed_within_cooldown():
    f = AlertFilter(cooldown_seconds=60)
    f.should_alert("svc/app.cfg", _now=T0)
    result = f.should_alert("svc/app.cfg", _now=T0 + 30)  # 30 s < 60 s
    assert result is False


def test_suppressed_count_does_not_increment():
    f = AlertFilter(cooldown_seconds=60)
    f.should_alert("svc/app.cfg", _now=T0)
    f.should_alert("svc/app.cfg", _now=T0 + 10)
    assert f.alert_count("svc/app.cfg") == 1


# ---------------------------------------------------------------------------
# Alert fires again after cooldown expires
# ---------------------------------------------------------------------------


def test_alert_fires_after_cooldown_elapsed():
    f = AlertFilter(cooldown_seconds=60)
    f.should_alert("svc/app.cfg", _now=T0)
    result = f.should_alert("svc/app.cfg", _now=T0 + 61)
    assert result is True


def test_count_increments_after_cooldown():
    f = AlertFilter(cooldown_seconds=60)
    f.should_alert("svc/app.cfg", _now=T0)
    f.should_alert("svc/app.cfg", _now=T0 + 61)
    assert f.alert_count("svc/app.cfg") == 2


# ---------------------------------------------------------------------------
# clear() resets state
# ---------------------------------------------------------------------------


def test_clear_allows_immediate_re_alert():
    f = AlertFilter(cooldown_seconds=300)
    f.should_alert("svc/db.conf", _now=T0)
    f.clear("svc/db.conf")
    assert f.should_alert("svc/db.conf", _now=T0 + 1) is True


def test_clear_resets_count():
    f = AlertFilter(cooldown_seconds=300)
    f.should_alert("svc/db.conf", _now=T0)
    f.clear("svc/db.conf")
    assert f.alert_count("svc/db.conf") == 0


def test_clear_nonexistent_target_is_noop():
    f = AlertFilter(cooldown_seconds=60)
    f.clear("ghost")  # should not raise


# ---------------------------------------------------------------------------
# suppressed_targets()
# ---------------------------------------------------------------------------


def test_suppressed_targets_lists_active_entries(monkeypatch):
    import time
    monkeypatch.setattr(time, "monotonic", lambda: T0 + 10)

    f = AlertFilter(cooldown_seconds=60)
    f.should_alert("a", _now=T0)
    f.should_alert("b", _now=T0)

    suppressed = f.suppressed_targets()
    assert "a" in suppressed
    assert "b" in suppressed


def test_suppressed_targets_excludes_expired(monkeypatch):
    import time
    monkeypatch.setattr(time, "monotonic", lambda: T0 + 120)

    f = AlertFilter(cooldown_seconds=60)
    f.should_alert("old", _now=T0)  # last_seen = T0, now = T0+120 → expired

    assert "old" not in f.suppressed_targets()
