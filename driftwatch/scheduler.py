"""Scheduler: runs the drift-check loop on a fixed interval."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from driftwatch.config import DriftWatchConfig
from driftwatch.runner import RunSummary, run_once

logger = logging.getLogger(__name__)


@dataclass
class SchedulerStats:
    """Accumulates statistics across scheduler iterations."""

    total_runs: int = 0
    total_drift: int = 0
    total_errors: int = 0
    last_summary: Optional[RunSummary] = field(default=None, repr=False)

    def record(self, summary: RunSummary) -> None:
        self.total_runs += 1
        self.total_drift += summary.drift_count
        self.total_errors += summary.error_count
        self.last_summary = summary


def run_loop(
    config: DriftWatchConfig,
    *,
    interval_seconds: Optional[float] = None,
    max_iterations: Optional[int] = None,
    _sleep: Callable[[float], None] = time.sleep,
) -> SchedulerStats:
    """Run the drift-check loop, blocking until *max_iterations* is reached.

    Parameters
    ----------
    config:
        Loaded ``DriftWatchConfig`` instance.
    interval_seconds:
        Seconds to sleep between iterations.  Falls back to
        ``config.interval_seconds`` when *None*.
    max_iterations:
        Stop after this many iterations.  ``None`` means run forever.
    _sleep:
        Injected sleep callable (used by tests to avoid real delays).
    """
    interval = interval_seconds if interval_seconds is not None else config.interval_seconds
    stats = SchedulerStats()
    iteration = 0

    logger.info(
        "Scheduler starting — interval=%.1fs targets=%d",
        interval,
        len(config.targets),
    )

    while max_iterations is None or iteration < max_iterations:
        logger.debug("Run #%d starting", iteration + 1)
        summary = run_once(config)
        stats.record(summary)

        logger.info(
            "Run #%d complete — drift=%d errors=%d",
            stats.total_runs,
            summary.drift_count,
            summary.error_count,
        )

        iteration += 1
        if max_iterations is None or iteration < max_iterations:
            _sleep(interval)

    logger.info(
        "Scheduler finished — total_runs=%d total_drift=%d total_errors=%d",
        stats.total_runs,
        stats.total_drift,
        stats.total_errors,
    )
    return stats
