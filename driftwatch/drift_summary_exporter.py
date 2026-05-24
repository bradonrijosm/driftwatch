"""Export drift summaries to JSON for external consumption (e.g. dashboards, CI gates)."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

from driftwatch.runner import RunSummary


@dataclass
class ExportedSummary:
    exported_at: float
    total_targets: int
    clean: int
    drifted: int
    errors: int
    has_drift: bool
    targets: List[dict]

    def as_dict(self) -> dict:
        return asdict(self)

    def as_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.as_dict(), indent=indent)


def build_export(summary: RunSummary, *, now: Optional[float] = None) -> ExportedSummary:
    """Convert a RunSummary into an ExportedSummary suitable for serialisation."""
    ts = now if now is not None else time.time()
    targets = []
    for target, drift_result in summary.results:
        targets.append({
            "name": target.name,
            "local_path": str(target.local_path),
            "remote_url": target.remote_url,
            "status": drift_result.status,
            "message": drift_result.message,
        })

    clean = sum(1 for _, r in summary.results if r.status == "ok")
    drifted = sum(1 for _, r in summary.results if r.status == "drift")
    errors = sum(1 for _, r in summary.results if r.status == "error")

    return ExportedSummary(
        exported_at=ts,
        total_targets=len(summary.results),
        clean=clean,
        drifted=drifted,
        errors=errors,
        has_drift=summary.has_drift,
        targets=targets,
    )


def write_export(summary: RunSummary, path: Path, *, now: Optional[float] = None) -> ExportedSummary:
    """Build and write an ExportedSummary to *path* as JSON. Returns the exported object."""
    exported = build_export(summary, now=now)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(exported.as_json(), encoding="utf-8")
    return exported
