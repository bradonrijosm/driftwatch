"""Runner: orchestrates a full drift-check cycle across all configured targets."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from driftwatch.checker import DriftResult, check_target
from driftwatch.config import DriftWatchConfig, WatchTarget
from driftwatch.fetcher import FetchError, fetch_remote
from driftwatch.notifier import notify

logger = logging.getLogger(__name__)


@dataclass
class RunSummary:
    """Aggregated results from a single run cycle."""

    total: int = 0
    clean: int = 0
    drifted: int = 0
    errored: int = 0
    results: List[DriftResult] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return self.drifted > 0 or self.errored > 0


def run_once(config: DriftWatchConfig) -> RunSummary:
    """Execute one full check cycle and return a summary.

    For each target:
      1. Fetch the remote content.
      2. Compare against the local file.
      3. Notify if drift or error is detected.
    """
    summary = RunSummary(total=len(config.targets))

    for target in config.targets:
        logger.debug("Checking target: %s", target.name)

        try:
            fetch_result = fetch_remote(target.remote_url, timeout=config.fetch_timeout)
        except FetchError as exc:
            logger.error("Fetch failed for %s: %s", target.name, exc)
            result = DriftResult(
                target=target,
                drifted=False,
                error=str(exc),
            )
        else:
            result = check_target(target, fetch_result)

        summary.results.append(result)

        if result.error:
            summary.errored += 1
            logger.warning("Error on %s: %s", target.name, result.error)
        elif result.drifted:
            summary.drifted += 1
            logger.warning("Drift detected on %s", target.name)
        else:
            summary.clean += 1
            logger.info("Clean: %s", target.name)

        notify(result, config.webhook_url)

    logger.info(
        "Run complete — total=%d clean=%d drifted=%d errored=%d",
        summary.total,
        summary.clean,
        summary.drifted,
        summary.errored,
    )
    return summary
