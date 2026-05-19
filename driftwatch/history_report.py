"""Render a human-readable summary of recent drift history."""

from __future__ import annotations

import datetime
from typing import List

from driftwatch.history import DriftEvent, HistoryStore

_STATUS_ICON = {
    "ok": "\u2705",      # ✅
    "drift": "\u26a0\ufe0f",  # ⚠️
    "error": "\u274c",   # ❌
}


def _fmt_ts(ts: float) -> str:
    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _fmt_event(ev: DriftEvent) -> str:
    icon = _STATUS_ICON.get(ev.status, "?")
    line = f"  {icon}  [{_fmt_ts(ev.checked_at)}]  {ev.target_name}  ({ev.status})"
    if ev.detail:
        line += f"\n       detail: {ev.detail}"
    return line


def build_history_report(events: List[DriftEvent]) -> str:
    """Return a multi-line string summarising *events*."""
    if not events:
        return "No history recorded yet.\n"

    total = len(events)
    drifted = sum(1 for e in events if e.status == "drift")
    errors = sum(1 for e in events if e.status == "error")

    header = (
        f"Drift history — {total} event(s)  "
        f"[drift: {drifted}  error: {errors}  ok: {total - drifted - errors}]\n"
        f"{'-' * 60}\n"
    )
    body = "\n".join(_fmt_event(e) for e in events)
    return header + body + "\n"


def print_history_report(store: HistoryStore, limit: int = 50) -> None:
    """Fetch recent events from *store* and print a report to stdout."""
    events = store.recent(limit=limit)
    print(build_history_report(events), end="")
