"""Drift suppression rules: skip alerting for targets matching tag or name patterns."""
from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass, field
from typing import Sequence

from driftwatch.config import WatchTarget

log = logging.getLogger(__name__)


@dataclass
class SuppressionRule:
    """A single suppression rule matched against target names or tags."""

    name_pattern: str = ""  # glob, e.g. "prod-*"
    tags: list[str] = field(default_factory=list)  # any tag match suppresses
    reason: str = ""

    def matches(self, target: WatchTarget) -> bool:
        """Return True if this rule suppresses *target*."""
        if self.name_pattern and fnmatch.fnmatch(target.name, self.name_pattern):
            log.debug(
                "Suppression rule '%s' matched target '%s' by name pattern",
                self.name_pattern,
                target.name,
            )
            return True
        target_tags: Sequence[str] = getattr(target, "tags", []) or []
        for tag in self.tags:
            if tag in target_tags:
                log.debug(
                    "Suppression rule tag '%s' matched target '%s'",
                    tag,
                    target.name,
                )
                return True
        return False


@dataclass
class SuppressionList:
    """Ordered collection of suppression rules."""

    rules: list[SuppressionRule] = field(default_factory=list)

    def is_suppressed(self, target: WatchTarget) -> bool:
        """Return True if *any* rule matches *target*."""
        for rule in self.rules:
            if rule.matches(target):
                return True
        return False

    def suppressed_reason(self, target: WatchTarget) -> str | None:
        """Return the reason string of the first matching rule, or None."""
        for rule in self.rules:
            if rule.matches(target):
                return rule.reason or "(no reason given)"
        return None

    def add(self, rule: SuppressionRule) -> None:
        self.rules.append(rule)

    def __len__(self) -> int:
        return len(self.rules)
