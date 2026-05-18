"""Configuration loader for driftwatch daemon."""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


DEFAULT_CONFIG_PATH = Path("/etc/driftwatch/config.toml")
FALLBACK_CONFIG_PATH = Path("~/.config/driftwatch/config.toml")


@dataclass
class WatchTarget:
    """A single file to monitor against a remote source."""
    local_path: str
    remote_url: str
    label: Optional[str] = None

    def __post_init__(self):
        if not self.local_path:
            raise ValueError("local_path must not be empty")
        if not self.remote_url:
            raise ValueError("remote_url must not be empty")


@dataclass
class DriftWatchConfig:
    """Top-level configuration for the driftwatch daemon."""
    poll_interval_seconds: int = 60
    alert_webhook_url: Optional[str] = None
    targets: list[WatchTarget] = field(default_factory=list)

    def __post_init__(self):
        if self.poll_interval_seconds < 5:
            raise ValueError("poll_interval_seconds must be at least 5")


def load_config(config_path: Optional[Path] = None) -> DriftWatchConfig:
    """Load and parse the TOML configuration file.

    Searches in order:
      1. Explicit path argument
      2. DRIFTWATCH_CONFIG env variable
      3. /etc/driftwatch/config.toml
      4. ~/.config/driftwatch/config.toml
    """
    candidates = []
    if config_path:
        candidates.append(Path(config_path))
    if env_path := os.environ.get("DRIFTWATCH_CONFIG"):
        candidates.append(Path(env_path))
    candidates.append(DEFAULT_CONFIG_PATH)
    candidates.append(FALLBACK_CONFIG_PATH.expanduser())

    for path in candidates:
        if path.exists():
            with open(path, "rb") as fh:
                raw = tomllib.load(fh)
            return _parse_config(raw)

    raise FileNotFoundError(
        "No driftwatch configuration file found. "
        "Checked: " + ", ".join(str(p) for p in candidates)
    )


def _parse_config(raw: dict) -> DriftWatchConfig:
    """Convert raw TOML dict into a DriftWatchConfig instance."""
    targets = [
        WatchTarget(
            local_path=t["local_path"],
            remote_url=t["remote_url"],
            label=t.get("label"),
        )
        for t in raw.get("targets", [])
    ]
    return DriftWatchConfig(
        poll_interval_seconds=raw.get("poll_interval_seconds", 60),
        alert_webhook_url=raw.get("alert_webhook_url"),
        targets=targets,
    )
