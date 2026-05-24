"""Baseline snapshot management for drift detection.

Allows capturing and comparing a known-good baseline digest for each
WatchTarget so that drift is measured relative to an explicit snapshot
rather than the live remote on every cycle.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class BaselineEntry:
    url: str
    digest: str
    captured_at: float  # Unix timestamp

    def age_seconds(self, now: Optional[float] = None) -> float:
        now = now if now is not None else time.time()
        return now - self.captured_at

    def as_dict(self) -> dict:
        return {
            "url": self.url,
            "digest": self.digest,
            "captured_at": self.captured_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BaselineEntry":
        return cls(
            url=data["url"],
            digest=data["digest"],
            captured_at=float(data["captured_at"]),
        )


@dataclass
class BaselineStore:
    _path: Path
    _entries: Dict[str, BaselineEntry] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
                self._entries = {
                    k: BaselineEntry.from_dict(v) for k, v in raw.items()
                }
            except (json.JSONDecodeError, KeyError):
                self._entries = {}

    def _save(self) -> None:
        self._path.write_text(
            json.dumps({k: v.as_dict() for k, v in self._entries.items()}, indent=2)
        )

    def set(self, url: str, digest: str, now: Optional[float] = None) -> BaselineEntry:
        entry = BaselineEntry(
            url=url,
            digest=digest,
            captured_at=now if now is not None else time.time(),
        )
        self._entries[url] = entry
        self._save()
        return entry

    def get(self, url: str) -> Optional[BaselineEntry]:
        return self._entries.get(url)

    def remove(self, url: str) -> bool:
        if url in self._entries:
            del self._entries[url]
            self._save()
            return True
        return False

    def all_entries(self) -> Dict[str, BaselineEntry]:
        return dict(self._entries)

    def __len__(self) -> int:
        return len(self._entries)
