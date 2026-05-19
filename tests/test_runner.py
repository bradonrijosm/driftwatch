"""Tests for driftwatch.runner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.checker import DriftResult
from driftwatch.config import DriftWatchConfig, WatchTarget
from driftwatch.fetcher import FetchError, FetchResult
from driftwatch.runner import RunSummary, run_once


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path, num_targets: int = 1) -> DriftWatchConfig:
    targets = [
        WatchTarget(
            name=f"target-{i}",
            local_path=str(tmp_path / f"cfg{i}.toml"),
            remote_url=f"https://example.com/cfg{i}.toml",
        )
        for i in range(num_targets)
    ]
    return DriftWatchConfig(
        targets=targets,
        webhook_url="https://hooks.example.com/alert",
        fetch_timeout=5,
        interval=60,
    )


def _clean_fetch() -> FetchResult:
    content = b"key = 'value'\n"
    return FetchResult(content=content, checksum="abc123", status_code=200)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch("driftwatch.runner.notify")
@patch("driftwatch.runner.check_target")
@patch("driftwatch.runner.fetch_remote")
def test_run_once_all_clean(mock_fetch, mock_check, mock_notify, tmp_path):
    config = _make_config(tmp_path, num_targets=2)
    mock_fetch.return_value = _clean_fetch()
    mock_check.return_value = DriftResult(target=config.targets[0], drifted=False)

    summary = run_once(config)

    assert summary.total == 2
    assert summary.clean == 2
    assert summary.drifted == 0
    assert summary.errored == 0
    assert not summary.has_drift
    assert mock_notify.call_count == 2


@patch("driftwatch.runner.notify")
@patch("driftwatch.runner.check_target")
@patch("driftwatch.runner.fetch_remote")
def test_run_once_drift_detected(mock_fetch, mock_check, mock_notify, tmp_path):
    config = _make_config(tmp_path)
    mock_fetch.return_value = _clean_fetch()
    mock_check.return_value = DriftResult(
        target=config.targets[0], drifted=True
    )

    summary = run_once(config)

    assert summary.drifted == 1
    assert summary.has_drift
    mock_notify.assert_called_once()


@patch("driftwatch.runner.notify")
@patch("driftwatch.runner.fetch_remote")
def test_run_once_fetch_error(mock_fetch, mock_notify, tmp_path):
    config = _make_config(tmp_path)
    mock_fetch.side_effect = FetchError("connection refused")

    summary = run_once(config)

    assert summary.errored == 1
    assert summary.clean == 0
    assert summary.has_drift
    result = summary.results[0]
    assert result.error == "connection refused"
    mock_notify.assert_called_once()


@patch("driftwatch.runner.notify")
@patch("driftwatch.runner.check_target")
@patch("driftwatch.runner.fetch_remote")
def test_run_summary_has_drift_false_when_all_clean(mock_fetch, mock_check, mock_notify, tmp_path):
    config = _make_config(tmp_path)
    mock_fetch.return_value = _clean_fetch()
    mock_check.return_value = DriftResult(target=config.targets[0], drifted=False)

    summary = run_once(config)
    assert summary.has_drift is False
