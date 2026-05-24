"""Tests for driftwatch.drift_annotator."""
from __future__ import annotations

import pytest

from driftwatch.checker import DriftResult
from driftwatch.config import WatchTarget
from driftwatch.drift_annotator import (
    AnnotatedDrift,
    Severity,
    annotate_results,
    has_critical,
    has_unknown,
)
from driftwatch.runner import RunSummary


def _target(name: str = "cfg") -> WatchTarget:
    return WatchTarget(name=name, local_path=f"/etc/{name}", remote_url=f"https://example.com/{name}")


def _ok_result() -> DriftResult:
    return DriftResult(drifted=False, error=None, local_checksum="abc", remote_checksum="abc")


def _drift_result() -> DriftResult:
    return DriftResult(drifted=True, error=None, local_checksum="abc", remote_checksum="xyz")


def _error_result() -> DriftResult:
    return DriftResult(drifted=False, error="connection refused", local_checksum=None, remote_checksum=None)


def _summary(pairs) -> RunSummary:
    return RunSummary(results=pairs)


# ---------------------------------------------------------------------------
# AnnotatedDrift.__str__
# ---------------------------------------------------------------------------

def test_str_ok_contains_check_mark():
    a = AnnotatedDrift(target_name="x", severity=Severity.OK, message="fine", recommendation="none")
    assert "✓" in str(a)
    assert "OK" in str(a)


def test_str_critical_contains_cross():
    a = AnnotatedDrift(target_name="x", severity=Severity.CRITICAL, message="bad", recommendation="fix")
    assert "✗" in str(a)
    assert "CRITICAL" in str(a)


def test_str_unknown_contains_question_mark():
    a = AnnotatedDrift(target_name="x", severity=Severity.UNKNOWN, message="?", recommendation="check")
    assert "?" in str(a)


# ---------------------------------------------------------------------------
# annotate_results
# ---------------------------------------------------------------------------

def test_annotate_ok_result():
    t = _target("app")
    summary = _summary([(t, _ok_result())])
    annotations = annotate_results(summary)
    assert len(annotations) == 1
    assert annotations[0].severity == Severity.OK
    assert annotations[0].target_name == "app"


def test_annotate_drift_result_is_critical():
    t = _target("app")
    summary = _summary([(t, _drift_result())])
    annotations = annotate_results(summary)
    assert annotations[0].severity == Severity.CRITICAL
    assert "differs" in annotations[0].message


def test_annotate_error_result_is_unknown():
    t = _target("app")
    summary = _summary([(t, _error_result())])
    annotations = annotate_results(summary)
    assert annotations[0].severity == Severity.UNKNOWN
    assert "connection refused" in annotations[0].message


def test_annotate_multiple_targets():
    targets = [_target("a"), _target("b"), _target("c")]
    results = [_ok_result(), _drift_result(), _error_result()]
    summary = _summary(list(zip(targets, results)))
    annotations = annotate_results(summary)
    assert len(annotations) == 3
    severities = [a.severity for a in annotations]
    assert Severity.OK in severities
    assert Severity.CRITICAL in severities
    assert Severity.UNKNOWN in severities


# ---------------------------------------------------------------------------
# has_critical / has_unknown
# ---------------------------------------------------------------------------

def test_has_critical_false_when_all_ok():
    t = _target()
    summary = _summary([(t, _ok_result())])
    assert not has_critical(annotate_results(summary))


def test_has_critical_true_when_drift():
    t = _target()
    summary = _summary([(t, _drift_result())])
    assert has_critical(annotate_results(summary))


def test_has_unknown_true_when_error():
    t = _target()
    summary = _summary([(t, _error_result())])
    assert has_unknown(annotate_results(summary))


def test_has_unknown_false_when_clean():
    t = _target()
    summary = _summary([(t, _ok_result())])
    assert not has_unknown(annotate_results(summary))


def test_recommendation_present_for_all_severities():
    targets = [_target("a"), _target("b"), _target("c")]
    results = [_ok_result(), _drift_result(), _error_result()]
    summary = _summary(list(zip(targets, results)))
    for annotation in annotate_results(summary):
        assert annotation.recommendation
