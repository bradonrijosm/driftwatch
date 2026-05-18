"""Tests for driftwatch configuration loader."""

import textwrap
import pytest
from pathlib import Path

from driftwatch.config import (
    DriftWatchConfig,
    WatchTarget,
    load_config,
    _parse_config,
)


MINIMAL_TOML = textwrap.dedent("""
    poll_interval_seconds = 30

    [[targets]]
    local_path = "/etc/app/settings.yaml"
    remote_url = "https://example.com/settings.yaml"
    label = "app-settings"
""")


def write_toml(tmp_path: Path, content: str) -> Path:
    cfg = tmp_path / "config.toml"
    cfg.write_text(content)
    return cfg


class TestWatchTarget:
    def test_valid_target(self):
        t = WatchTarget(local_path="/etc/foo", remote_url="https://x.com/foo")
        assert t.local_path == "/etc/foo"

    def test_empty_local_path_raises(self):
        with pytest.raises(ValueError, match="local_path"):
            WatchTarget(local_path="", remote_url="https://x.com/foo")

    def test_empty_remote_url_raises(self):
        with pytest.raises(ValueError, match="remote_url"):
            WatchTarget(local_path="/etc/foo", remote_url="")


class TestDriftWatchConfig:
    def test_defaults(self):
        cfg = DriftWatchConfig()
        assert cfg.poll_interval_seconds == 60
        assert cfg.alert_webhook_url is None
        assert cfg.targets == []

    def test_interval_too_small_raises(self):
        with pytest.raises(ValueError, match="poll_interval_seconds"):
            DriftWatchConfig(poll_interval_seconds=3)


class TestParseConfig:
    def test_parses_minimal_config(self):
        raw = {
            "poll_interval_seconds": 30,
            "targets": [
                {"local_path": "/etc/foo", "remote_url": "https://x.com/foo"}
            ],
        }
        cfg = _parse_config(raw)
        assert cfg.poll_interval_seconds == 30
        assert len(cfg.targets) == 1
        assert cfg.targets[0].local_path == "/etc/foo"

    def test_parses_empty_targets(self):
        cfg = _parse_config({})
        assert cfg.targets == []

    def test_parses_webhook_url(self):
        cfg = _parse_config({"alert_webhook_url": "https://hooks.example.com/abc"})
        assert cfg.alert_webhook_url == "https://hooks.example.com/abc"


class TestLoadConfig:
    def test_loads_from_explicit_path(self, tmp_path):
        cfg_path = write_toml(tmp_path, MINIMAL_TOML)
        cfg = load_config(cfg_path)
        assert isinstance(cfg, DriftWatchConfig)
        assert cfg.poll_interval_seconds == 30
        assert cfg.targets[0].label == "app-settings"

    def test_loads_from_env_variable(self, tmp_path, monkeypatch):
        cfg_path = write_toml(tmp_path, MINIMAL_TOML)
        monkeypatch.setenv("DRIFTWATCH_CONFIG", str(cfg_path))
        cfg = load_config()
        assert cfg.poll_interval_seconds == 30

    def test_raises_when_no_config_found(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DRIFTWATCH_CONFIG", raising=False)
        # Point default paths somewhere that doesn't exist
        import driftwatch.config as cfg_module
        monkeypatch.setattr(cfg_module, "DEFAULT_CONFIG_PATH", tmp_path / "nope.toml")
        monkeypatch.setattr(cfg_module, "FALLBACK_CONFIG_PATH", tmp_path / "also_nope.toml")
        with pytest.raises(FileNotFoundError):
            load_config()
