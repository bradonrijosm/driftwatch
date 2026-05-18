"""Drift checker: compares local config files against remote source of truth."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from driftwatch.config import WatchTarget
from driftwatch.fetcher import FetchError, checksum_of_bytes, fetch_remote

logger = logging.getLogger(__name__)


@dataclass
class DriftResult:
    target: WatchTarget
    local_checksum: str
    remote_checksum: str
    drifted: bool
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and not self.drifted


def check_target(target: WatchTarget) -> DriftResult:
    """Compare a single WatchTarget's local file to its remote URL.

    Returns a DriftResult describing whether drift was detected.
    """
    local_path = Path(target.local_path)

    if not local_path.exists():
        logger.warning("Local file not found: %s", local_path)
        return DriftResult(
            target=target,
            local_checksum="",
            remote_checksum="",
            drifted=True,
            error=f"Local file not found: {local_path}",
        )

    local_bytes = local_path.read_bytes()
    local_checksum = checksum_of_bytes(local_bytes)

    try:
        fetch_result = fetch_remote(target.remote_url)
    except FetchError as exc:
        logger.error("Failed to fetch remote for target '%s': %s", target.name, exc)
        return DriftResult(
            target=target,
            local_checksum=local_checksum,
            remote_checksum="",
            drifted=False,
            error=str(exc),
        )

    drifted = local_checksum != fetch_result.checksum
    if drifted:
        logger.warning(
            "Drift detected for '%s': local=%s remote=%s",
            target.name,
            local_checksum,
            fetch_result.checksum,
        )
    else:
        logger.info("No drift for '%s'", target.name)

    return DriftResult(
        target=target,
        local_checksum=local_checksum,
        remote_checksum=fetch_result.checksum,
        drifted=drifted,
    )
