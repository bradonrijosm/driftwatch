"""Tests for driftwatch.notifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from driftwatch.checker import DriftResult
from driftwatch.config import WatchTarget
from driftwatch.notifier import notify, _format_alert, _build_payload


@pytest.fixture()
def drifted_target() -> WatchTarget:
    return WatchTarget(name="app-config", local_path="/etc/app.conf", remote_url="https://example.com/app.conf")


@pytest.fixture()
def drifted_result(drifted_target: WatchTarget) -> DriftResult:
    return DriftResult(target=drifted_target, drifted=True)


@pytest.fixture()
def error_result(drifted_target: WatchTarget) -> DriftResult:
    return DriftResult(target=drifted_target, drifted=False, error="file not found")


@pytest.fixture()
def clean_result(drifted_target: WatchTarget) -> DriftResult:
    return DriftResult(target=drifted_target, drifted=False)


def test_no_notification_when_clean(clean_result: DriftResult, capsys):
    result = notify(clean_result)
    assert result.success is True
    assert "no drift" in result.message
    captured = capsys.readouterr()
    assert captured.out == ""


def test_drift_prints_alert(drifted_result: DriftResult, capsys):
    result = notify(drifted_result)
    assert result.success is True
    captured = capsys.readouterr()
    assert "DRIFT" in captured.out
    assert "app-config" in captured.out


def test_error_prints_alert(error_result: DriftResult, capsys):
    result = notify(error_result)
    assert result.success is True
    captured = capsys.readouterr()
    assert "ERROR" in captured.out
    assert "file not found" in captured.out


def test_format_alert_contains_target_name(drifted_result: DriftResult):
    text = _format_alert(drifted_result)
    assert "app-config" in text
    assert "DRIFT" in text


def test_build_payload_keys(drifted_result: DriftResult):
    payload = _build_payload(drifted_result)
    assert payload["target"] == "app-config"
    assert payload["drifted"] is True
    assert "timestamp" in payload


def test_webhook_called_on_drift(drifted_result: DriftResult):
    mock_response = MagicMock(status_code=200)
    with patch("driftwatch.notifier.httpx.post", return_value=mock_response) as mock_post:
        result = notify(drifted_result, webhook_url="https://hooks.example.com/alert")
    assert result.success is True
    assert result.webhook_status_code == 200
    mock_post.assert_called_once()


def test_webhook_failure_returns_unsuccessful(drifted_result: DriftResult):
    with patch("driftwatch.notifier.httpx.post", side_effect=httpx.ConnectError("refused")):
        result = notify(drifted_result, webhook_url="https://hooks.example.com/alert")
    assert result.success is False
    assert "webhook failed" in result.message
    assert result.webhook_status_code is None


def test_no_webhook_call_when_url_omitted(drifted_result: DriftResult):
    with patch("driftwatch.notifier.httpx.post") as mock_post:
        notify(drifted_result)
    mock_post.assert_not_called()
