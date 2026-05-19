"""Tests for the driftwatch CLI entry-point."""

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.cli import main
from driftwatch.runner import RunSummary
from driftwatch.checker import DriftResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_config(tmp_path: Path, extra: str = "") -> Path:
    cfg = tmp_path / "driftwatch.toml"
    cfg.write_text(
        textwrap.dedent(
            f"""
            [slack]
            webhook_url = "https://hooks.slack.com/test"

            [[targets]]
            name = "hosts"
            local_path = "/etc/hosts"
            remote_url = "https://example.com/hosts"
            {extra}
            """
        )
    )
    return cfg


def _clean_summary() -> RunSummary:
    result = MagicMock()
    result.drift_result = DriftResult(drifted=False, error=False, message="ok")
    summary = MagicMock(spec=RunSummary)
    summary.results = [result]
    summary.has_drift = False
    return summary


def _drifted_summary() -> RunSummary:
    result = MagicMock()
    result.drift_result = DriftResult(drifted=True, error=False, message="drift")
    summary = MagicMock(spec=RunSummary)
    summary.results = [result]
    summary.has_drift = True
    return summary


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_check_returns_0_when_no_drift(tmp_path):
    cfg_file = _write_config(tmp_path)
    with patch("driftwatch.cli.run_once", return_value=_clean_summary()):
        code = main(["-c", str(cfg_file), "check"])
    assert code == 0


def test_check_returns_1_when_drift(tmp_path):
    cfg_file = _write_config(tmp_path)
    with patch("driftwatch.cli.run_once", return_value=_drifted_summary()):
        code = main(["-c", str(cfg_file), "check"])
    assert code == 1


def test_missing_config_returns_1(tmp_path):
    code = main(["-c", str(tmp_path / "missing.toml"), "check"])
    assert code == 1


def test_daemon_command_calls_run_loop(tmp_path):
    cfg_file = _write_config(tmp_path)
    with patch("driftwatch.cli.run_loop", side_effect=KeyboardInterrupt) as mock_loop:
        code = main(["-c", str(cfg_file), "daemon"])
    mock_loop.assert_called_once()
    assert code == 0


def test_default_command_is_daemon(tmp_path):
    cfg_file = _write_config(tmp_path)
    with patch("driftwatch.cli.run_loop", side_effect=KeyboardInterrupt) as mock_loop:
        main(["-c", str(cfg_file)])
    mock_loop.assert_called_once()


def test_verbose_flag_accepted(tmp_path):
    cfg_file = _write_config(tmp_path)
    with patch("driftwatch.cli.run_once", return_value=_clean_summary()):
        code = main(["-c", str(cfg_file), "-v", "check"])
    assert code == 0
