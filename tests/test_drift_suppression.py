"""Tests for driftwatch.drift_suppression."""
from __future__ import annotations

import pytest

from driftwatch.drift_suppression import SuppressionList, SuppressionRule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeTarget:
    """Minimal stand-in for WatchTarget."""

    def __init__(self, name: str, tags: list[str] | None = None):
        self.name = name
        self.tags = tags or []


# ---------------------------------------------------------------------------
# SuppressionRule.matches
# ---------------------------------------------------------------------------

def test_name_pattern_exact_match():
    rule = SuppressionRule(name_pattern="prod-db")
    assert rule.matches(_FakeTarget("prod-db")) is True


def test_name_pattern_glob_match():
    rule = SuppressionRule(name_pattern="prod-*")
    assert rule.matches(_FakeTarget("prod-api")) is True


def test_name_pattern_no_match():
    rule = SuppressionRule(name_pattern="prod-*")
    assert rule.matches(_FakeTarget("staging-api")) is False


def test_tag_match():
    rule = SuppressionRule(tags=["readonly"])
    assert rule.matches(_FakeTarget("any", tags=["readonly", "infra"])) is True


def test_tag_no_match():
    rule = SuppressionRule(tags=["readonly"])
    assert rule.matches(_FakeTarget("any", tags=["infra"])) is False


def test_empty_rule_never_matches():
    rule = SuppressionRule()
    assert rule.matches(_FakeTarget("anything")) is False


def test_target_without_tags_attribute():
    """Targets that lack a tags attribute should not crash."""
    rule = SuppressionRule(tags=["critical"])

    class _NoTags:
        name = "bare-target"

    assert rule.matches(_NoTags()) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SuppressionList
# ---------------------------------------------------------------------------

def test_empty_list_never_suppresses():
    sl = SuppressionList()
    assert sl.is_suppressed(_FakeTarget("anything")) is False


def test_is_suppressed_true_when_rule_matches():
    sl = SuppressionList(rules=[SuppressionRule(name_pattern="canary-*")])
    assert sl.is_suppressed(_FakeTarget("canary-west")) is True


def test_is_suppressed_false_when_no_rule_matches():
    sl = SuppressionList(rules=[SuppressionRule(name_pattern="canary-*")])
    assert sl.is_suppressed(_FakeTarget("prod-west")) is False


def test_suppressed_reason_returns_none_when_not_matched():
    sl = SuppressionList(rules=[SuppressionRule(name_pattern="x-*", reason="test")])
    assert sl.suppressed_reason(_FakeTarget("prod-db")) is None


def test_suppressed_reason_returns_first_match():
    sl = SuppressionList(
        rules=[
            SuppressionRule(name_pattern="prod-*", reason="prod freeze"),
            SuppressionRule(name_pattern="prod-db", reason="db maintenance"),
        ]
    )
    assert sl.suppressed_reason(_FakeTarget("prod-db")) == "prod freeze"


def test_suppressed_reason_default_when_empty_reason():
    sl = SuppressionList(rules=[SuppressionRule(name_pattern="*")])
    assert sl.suppressed_reason(_FakeTarget("any")) == "(no reason given)"


def test_add_increases_length():
    sl = SuppressionList()
    assert len(sl) == 0
    sl.add(SuppressionRule(name_pattern="foo"))
    assert len(sl) == 1


def test_multiple_rules_first_matching_wins():
    sl = SuppressionList(
        rules=[
            SuppressionRule(tags=["skip"], reason="tagged skip"),
            SuppressionRule(name_pattern="legacy-*", reason="legacy"),
        ]
    )
    target = _FakeTarget("legacy-svc", tags=["skip"])
    assert sl.suppressed_reason(target) == "tagged skip"
