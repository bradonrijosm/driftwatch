"""Persistent cache for remote content digests to avoid redundant fetches."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_DEFAULT_TTL = 300  # seconds


@dataclass
class CacheEntry:
    checksum: str
    fetched_at: float
    url: str

    def is_fresh(self, ttl: int = _DEFAULT_TTL) -> bool:
        return (time.time() - self.fetched_at) < ttl


@dataclass
class DigestCache:
    cache_path: Path
    ttl: int = _DEFAULT_TTL
    _entries: dict[str, CacheEntry] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if self.cache_path.exists():
            try:
                raw = json.loads(self.cache_path.read_text())
                self._entries = {
                    k: CacheEntry(**v) for k, v in raw.items()
                }
                log.debug("Loaded %d digest cache entries", len(self._entries))
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not load digest cache: %s", exc)
                self._entries = {}

    def _save(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            data = {k: vars(v) for k, v in self._entries.items()}
            self.cache_path.write_text(json.dumps(data, indent=2))
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not save digest cache: %s", exc)

    def get(self, url: str) -> Optional[CacheEntry]:
        entry = self._entries.get(url)
        if entry and entry.is_fresh(self.ttl):
            return entry
        return None

    def put(self, url: str, checksum: str) -> CacheEntry:
        entry = CacheEntry(checksum=checksum, fetched_at=time.time(), url=url)
        self._entries[url] = entry
        self._save()
        return entry

    def invalidate(self, url: str) -> None:
        self._entries.pop(url, None)
        self._save()

    def __len__(self) -> int:
        return len(self._entries)
