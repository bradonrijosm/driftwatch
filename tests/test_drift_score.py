"""Tests for driftwatch.drift_score."""
from __future__ import annotations

import pytest

from driftwatch.checker import DriftResult
from driftwatch.config import WatchTarget
from driftwatch.drift_score import (
    AggregateScore,
    TargetScore,
    aggregate_scores,
    score_result,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _target(name: str = "cfg") -> WatchTarget:
    return WatchTarget(name=name, local_path="/tmp/f", remote_url="https://example.com/f")


def _ok(name: str = "cfg") -> DriftResult:
    return DriftResult(target=_target(name), drifted=False, error=None)


def _drift(name: str = "cfg") -> DriftResult:
    return DriftResult(target=_target(name), drifted=True, error=None)


def _error(name: str = "cfg", msg: str = "timeout") -> DriftResult:
    return DriftResult(target=_target(name), drifted=False, error=msg)


# ---------------------------------------------------------------------------
# TargetScore
# ---------------------------------------------------------------------------

class TestTargetScore:
    def test_clean_score_is_zero(self):
        ts = TargetScore(target_name="x", score=0, reason="ok")
        assert ts.is_clean

    def test_nonzero_score_is_not_clean(self):
        ts = TargetScore(target_name="x", score=5, reason="error")
        assert not ts.is_clean


# ---------------------------------------------------------------------------
# score_result
# ---------------------------------------------------------------------------

def test_ok_result_scores_zero():
    ts = score_result(_ok())
    assert ts.score == 0
    assert ts.is_clean
    assert ts.reason == "ok"


def test_drifted_result_scores_ten():
    ts = score_result(_drift())
    assert ts.score == 10
    assert not ts.is_clean
    assert "mismatch" in ts.reason


def test_error_result_scores_five():
    ts = score_result(_error(msg="conn refused"))
    assert ts.score == 5
    assert "conn refused" in ts.reason


def test_target_name_preserved():
    ts = score_result(_ok(name="my-config"))
    assert ts.target_name == "my-config"


# ---------------------------------------------------------------------------
# aggregate_scores
# ---------------------------------------------------------------------------

def test_all_clean_aggregate_is_zero():
    agg = aggregate_scores([_ok("a"), _ok("b")])
    assert agg.total == 0
    assert agg.is_clean


def test_mixed_aggregate_sums_correctly():
    # drift(10) + error(5) + ok(0) = 15
    agg = aggregate_scores([_drift("a"), _error("b"), _ok("c")])
    assert agg.total == 15
    assert not agg.is_clean


def test_worst_returns_highest_score():
    agg = aggregate_scores([_drift("a"), _error("b"), _ok("c")])
    assert agg.worst is not None
    assert agg.worst.target_name == "a"
    assert agg.worst.score == 10


def test_worst_is_none_for_empty_list():
    agg = aggregate_scores([])
    assert agg.worst is None
    assert agg.is_clean


def test_aggregate_preserves_all_target_scores():
    agg = aggregate_scores([_ok("x"), _drift("y")])
    names = {ts.target_name for ts in agg.target_scores}
    assert names == {"x", "y"}
