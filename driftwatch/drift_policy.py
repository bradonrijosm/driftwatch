"""drift_policy.py — Defines per-target and global drift policies.

A policy controls how driftwatch reacts to a detected drift or error:
  - whether to treat the result as an actionable alert
  - the minimum severity threshold required to notify
  - whether errors (fetch failures) should be treated like drift

Policies are matched by target name (exact or glob).  The first matching
rule wins; a built-in default catches everything that has no explicit rule.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import List, Optional

from driftwatch.drift_annotator import Severity


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PolicyRule:
    """A single named policy rule.

    Attributes:
        name_pattern: Glob pattern matched against the target name.
            Use ``"*"`` to create a catch-all default.
        min_severity: Minimum :class:`~driftwatch.drift_annotator.Severity`
            required before a notification is sent.
        alert_on_error: When *True* a fetch/check error triggers an alert
            even if no content drift was detected.
        enabled: When *False* the rule suppresses all alerts for matching
            targets (acts as an explicit silence).
    """

    name_pattern: str
    min_severity: Severity = Severity.LOW
    alert_on_error: bool = True
    enabled: bool = True

    def matches(self, target_name: str) -> bool:
        """Return *True* when *target_name* matches :attr:`name_pattern`."""
        return fnmatch.fnmatch(target_name, self.name_pattern)


@dataclass
class DriftPolicy:
    """Ordered collection of :class:`PolicyRule` objects.

    Rules are evaluated in insertion order; the first match is used.  If no
    rule matches, :attr:`default_rule` is applied.
    """

    rules: List[PolicyRule] = field(default_factory=list)
    default_rule: PolicyRule = field(
        default_factory=lambda: PolicyRule(
            name_pattern="*",
            min_severity=Severity.LOW,
            alert_on_error=True,
            enabled=True,
        )
    )

    def add_rule(self, rule: PolicyRule) -> None:
        """Append *rule* to the end of the rule list."""
        self.rules.append(rule)

    def resolve(self, target_name: str) -> PolicyRule:
        """Return the first rule whose pattern matches *target_name*.

        Falls back to :attr:`default_rule` when nothing matches.
        """
        for rule in self.rules:
            if rule.matches(target_name):
                return rule
        return self.default_rule


# ---------------------------------------------------------------------------
# Decision helper
# ---------------------------------------------------------------------------

@dataclass
class PolicyDecision:
    """Result of evaluating a policy against a specific target outcome."""

    should_alert: bool
    rule: PolicyRule
    reason: str


def evaluate_policy(
    policy: DriftPolicy,
    target_name: str,
    severity: Optional[Severity],
    is_error: bool,
) -> PolicyDecision:
    """Decide whether to alert based on *policy* and the current outcome.

    Parameters
    ----------
    policy:
        The :class:`DriftPolicy` to consult.
    target_name:
        Name of the watch target being evaluated.
    severity:
        Detected :class:`~driftwatch.drift_annotator.Severity`, or *None*
        when the result is clean.
    is_error:
        *True* when the check ended in a fetch / IO error.

    Returns
    -------
    PolicyDecision
        A record describing the outcome and the matched rule.
    """
    rule = policy.resolve(target_name)

    if not rule.enabled:
        return PolicyDecision(
            should_alert=False,
            rule=rule,
            reason="rule disabled — alerts silenced for this target",
        )

    if is_error:
        if rule.alert_on_error:
            return PolicyDecision(
                should_alert=True,
                rule=rule,
                reason="error detected and alert_on_error is enabled",
            )
        return PolicyDecision(
            should_alert=False,
            rule=rule,
            reason="error detected but alert_on_error is disabled",
        )

    if severity is None:
        return PolicyDecision(
            should_alert=False,
            rule=rule,
            reason="no drift detected",
        )

    if severity >= rule.min_severity:
        return PolicyDecision(
            should_alert=True,
            rule=rule,
            reason=f"severity {severity.name} meets threshold {rule.min_severity.name}",
        )

    return PolicyDecision(
        should_alert=False,
        rule=rule,
        reason=(
            f"severity {severity.name} below threshold {rule.min_severity.name}"
        ),
    )
