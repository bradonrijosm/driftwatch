"""Annotates drift results with human-readable severity levels and recommendations."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from driftwatch.checker import DriftResult
from driftwatch.runner import RunSummary


class Severity(str, Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AnnotatedDrift:
    target_name: str
    severity: Severity
    message: str
    recommendation: str

    def __str__(self) -> str:
        icon = {Severity.OK: "✓", Severity.WARNING: "⚠", Severity.CRITICAL: "✗", Severity.UNKNOWN: "?"}[
            self.severity
        ]
        return f"{icon} [{self.severity.value.upper()}] {self.target_name}: {self.message}"


def _classify(result: DriftResult) -> tuple[Severity, str, str]:
    """Return (severity, message, recommendation) for a single DriftResult."""
    if result.error:
        return (
            Severity.UNKNOWN,
            f"Check failed: {result.error}",
            "Verify the remote URL is reachable and the local path exists.",
        )
    if result.drifted:
        return (
            Severity.CRITICAL,
            "Local file differs from remote source of truth.",
            "Review the diff and update the local file or acknowledge the change.",
        )
    return (
        Severity.OK,
        "Local file matches remote source of truth.",
        "No action required.",
    )


def annotate_results(summary: RunSummary) -> List[AnnotatedDrift]:
    """Return an AnnotatedDrift for every target in *summary*."""
    annotations: List[AnnotatedDrift] = []
    for target, result in summary.results:
        severity, message, recommendation = _classify(result)
        annotations.append(
            AnnotatedDrift(
                target_name=target.name,
                severity=severity,
                message=message,
                recommendation=recommendation,
            )
        )
    return annotations


def has_critical(annotations: List[AnnotatedDrift]) -> bool:
    return any(a.severity == Severity.CRITICAL for a in annotations)


def has_unknown(annotations: List[AnnotatedDrift]) -> bool:
    return any(a.severity == Severity.UNKNOWN for a in annotations)
