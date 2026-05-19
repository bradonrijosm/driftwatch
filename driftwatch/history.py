"""Persistent drift history: records check results to a local SQLite database."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

DEFAULT_DB_PATH = Path("~/.local/share/driftwatch/history.db").expanduser()

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS drift_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target_name TEXT    NOT NULL,
    local_path  TEXT    NOT NULL,
    remote_url  TEXT    NOT NULL,
    status      TEXT    NOT NULL,  -- 'ok' | 'drift' | 'error'
    detail      TEXT,
    checked_at  REAL    NOT NULL   -- Unix timestamp
);
"""


@dataclass
class DriftEvent:
    target_name: str
    local_path: str
    remote_url: str
    status: str
    detail: Optional[str]
    checked_at: float
    id: Optional[int] = None


class HistoryStore:
    """Thin wrapper around a SQLite database for storing drift events."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute(CREATE_TABLE_SQL)
        self._conn.commit()

    # ------------------------------------------------------------------
    def record(self, event: DriftEvent) -> int:
        """Insert *event* and return the new row id."""
        cur = self._conn.execute(
            "INSERT INTO drift_events "
            "(target_name, local_path, remote_url, status, detail, checked_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                event.target_name,
                event.local_path,
                event.remote_url,
                event.status,
                event.detail,
                event.checked_at,
            ),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def recent(self, limit: int = 50) -> List[DriftEvent]:
        """Return the *limit* most recent events, newest first."""
        rows = self._conn.execute(
            "SELECT id, target_name, local_path, remote_url, status, detail, checked_at "
            "FROM drift_events ORDER BY checked_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            DriftEvent(
                id=r[0],
                target_name=r[1],
                local_path=r[2],
                remote_url=r[3],
                status=r[4],
                detail=r[5],
                checked_at=r[6],
            )
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()


def record_run_summary(store: HistoryStore, summary: object, ts: Optional[float] = None) -> None:
    """Persist every DriftResult in *summary* to *store*."""
    from driftwatch.checker import DriftResult  # local import to avoid cycles

    now = ts if ts is not None else time.time()
    for result in summary.results:  # type: ignore[attr-defined]
        status = "error" if result.error else ("drift" if result.drifted else "ok")
        store.record(
            DriftEvent(
                target_name=result.target.name,
                local_path=result.target.local_path,
                remote_url=result.target.remote_url,
                status=status,
                detail=result.error or None,
                checked_at=now,
            )
        )
