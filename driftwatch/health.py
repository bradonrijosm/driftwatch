"""Health check endpoint data for driftwatch daemon status."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Any

from driftwatch.metrics import MetricsCollector
from driftwatch.target_status import StatusMap


@dataclass
class HealthStatus:
    """Snapshot of daemon health at a point in time."""
    healthy: bool
    uptime_seconds: float
    checks_run: int
    drift_count: int
    error_count: int
    target_statuses: Dict[str, str]
    timestamp: float = field(default_factory=time.time)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "healthy": self.healthy,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "checks_run": self.checks_run,
            "drift_count": self.drift_count,
            "error_count": self.error_count,
            "target_statuses": self.target_statuses,
            "timestamp": self.timestamp,
        }


class HealthReporter:
    """Builds HealthStatus from live daemon state."""

    def __init__(self, metrics: MetricsCollector, status_map: StatusMap) -> None:
        self._metrics = metrics
        self._status_map = status_map
        self._started_at: float = time.time()

    def snapshot(self) -> HealthStatus:
        snap = self._metrics.snapshot()
        checks_run = snap.get("checks_run")
        drift_count = snap.get("drift_detected")
        error_count = snap.get("fetch_errors")

        target_statuses: Dict[str, str] = {}
        for entry in self._status_map.entries():
            target_statuses[entry.target.local_path] = entry.status.value

        healthy = error_count == 0 and drift_count == 0

        return HealthStatus(
            healthy=healthy,
            uptime_seconds=time.time() - self._started_at,
            checks_run=checks_run,
            drift_count=drift_count,
            error_count=error_count,
            target_statuses=target_statuses,
        )

    def reset_start_time(self) -> None:
        """Reset uptime clock (useful for testing)."""
        self._started_at = time.time()
