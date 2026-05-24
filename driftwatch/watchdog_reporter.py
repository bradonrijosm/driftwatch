"""Formats a human-readable health summary from a Watchdog instance."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from driftwatch.watchdog import Watchdog

_HEALTHY_ICON = "\u2705"   # ✅
_UNHEALTHY_ICON = "\u274c"  # ❌


@dataclass(frozen=True)
class WatchdogReport:
    total: int
    healthy: int
    unhealthy: int
    lines: Sequence[str]

    @property
    def all_healthy(self) -> bool:
        return self.unhealthy == 0


def build_watchdog_report(dog: Watchdog, target_names: Sequence[str]) -> WatchdogReport:
    """Build a :class:`WatchdogReport` for *target_names* using *dog*."""
    rows: list[str] = []
    healthy_count = 0

    for name in target_names:
        ok = dog.is_healthy(name)
        icon = _HEALTHY_ICON if ok else _UNHEALTHY_ICON
        failures = dog.consecutive_failures(name)
        successes = dog.consecutive_successes(name)
        detail = f"failures={failures} successes={successes}"
        rows.append(f"  {icon}  {name:<30s}  {detail}")
        if ok:
            healthy_count += 1

    unhealthy_count = len(target_names) - healthy_count
    header = (
        f"Watchdog health — "
        f"{healthy_count}/{len(target_names)} healthy"
        f"{'' if unhealthy_count == 0 else f', {unhealthy_count} UNHEALTHY'}"
    )
    lines = [header, "-" * len(header)] + rows
    return WatchdogReport(
        total=len(target_names),
        healthy=healthy_count,
        unhealthy=unhealthy_count,
        lines=lines,
    )


def print_watchdog_report(dog: Watchdog, target_names: Sequence[str]) -> None:  # pragma: no cover
    report = build_watchdog_report(dog, target_names)
    for line in report.lines:
        print(line)
