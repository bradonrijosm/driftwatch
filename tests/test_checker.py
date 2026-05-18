"""Tests for driftwatch.checker."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from driftwatch.checker import DriftResult, check_target
from driftwatch.config import WatchTarget
from driftwatch.fetcher import checksum_of_bytes


LOCAL_CONTENT = b"[app]\nversion = 1\n"
REMOTE_CONTENT_SAME = LOCAL_CONTENT
REMOTE_CONTENT_DIFFERENT = b"[app]\nversion = 2\n"


@pytest.fixture()
def local_config_file(tmp_path: Path) -> Path:
    cfg = tmp_path / "app.toml"
    cfg.write_bytes(LOCAL_CONTENT)
    return cfg


def _make_target(local_path: str, remote_url: str) -> WatchTarget:
    return WatchTarget(name="test-target", local_path=local_path, remote_url=remote_url)


def test_no_drift_when_content_matches(httpx_mock: HTTPXMock, local_config_file: Path):
    url = "https://example.com/app.toml"
    httpx_mock.add_response(url=url, content=REMOTE_CONTENT_SAME, status_code=200)

    target = _make_target(str(local_config_file), url)
    result = check_target(target)

    assert isinstance(result, DriftResult)
    assert not result.drifted
    assert result.error is None
    assert result.ok
    assert result.local_checksum == checksum_of_bytes(LOCAL_CONTENT)


def test_drift_detected_when_content_differs(httpx_mock: HTTPXMock, local_config_file: Path):
    url = "https://example.com/app.toml"
    httpx_mock.add_response(url=url, content=REMOTE_CONTENT_DIFFERENT, status_code=200)

    target = _make_target(str(local_config_file), url)
    result = check_target(target)

    assert result.drifted
    assert result.error is None
    assert not result.ok
    assert result.remote_checksum == checksum_of_bytes(REMOTE_CONTENT_DIFFERENT)


def test_error_when_local_file_missing(httpx_mock: HTTPXMock, tmp_path: Path):
    url = "https://example.com/app.toml"
    missing = str(tmp_path / "nonexistent.toml")

    target = _make_target(missing, url)
    result = check_target(target)

    assert result.drifted
    assert result.error is not None
    assert "not found" in result.error
    assert not result.ok


def test_error_when_remote_fetch_fails(httpx_mock: HTTPXMock, local_config_file: Path):
    url = "https://example.com/app.toml"
    httpx_mock.add_response(url=url, status_code=503)

    target = _make_target(str(local_config_file), url)
    result = check_target(target)

    assert result.error is not None
    assert "HTTP 503" in result.error
    assert not result.drifted  # unknown state, not marked as drifted
    assert not result.ok
