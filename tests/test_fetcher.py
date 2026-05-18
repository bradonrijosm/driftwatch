"""Tests for driftwatch.fetcher."""

from __future__ import annotations

import pytest
import httpx
from pytest_httpx import HTTPXMock

from driftwatch.fetcher import FetchError, FetchResult, checksum_of_bytes, fetch_remote


SAMPLE_CONTENT = b"[settings]\nkey = value\n"


def test_checksum_of_bytes_is_deterministic():
    digest = checksum_of_bytes(SAMPLE_CONTENT)
    assert checksum_of_bytes(SAMPLE_CONTENT) == digest
    assert len(digest) == 64  # SHA-256 hex


def test_checksum_differs_for_different_content():
    assert checksum_of_bytes(b"abc") != checksum_of_bytes(b"xyz")


def test_fetch_remote_success(httpx_mock: HTTPXMock):
    url = "https://example.com/config.toml"
    httpx_mock.add_response(url=url, content=SAMPLE_CONTENT, status_code=200)

    result = fetch_remote(url)

    assert isinstance(result, FetchResult)
    assert result.url == url
    assert result.content == SAMPLE_CONTENT
    assert result.status_code == 200
    assert result.checksum == checksum_of_bytes(SAMPLE_CONTENT)


def test_fetch_remote_http_error(httpx_mock: HTTPXMock):
    url = "https://example.com/missing.toml"
    httpx_mock.add_response(url=url, status_code=404)

    with pytest.raises(FetchError, match="HTTP 404"):
        fetch_remote(url)


def test_fetch_remote_connection_error(httpx_mock: HTTPXMock):
    url = "https://unreachable.example.com/config.toml"
    httpx_mock.add_exception(httpx.ConnectError("connection refused"))

    with pytest.raises(FetchError, match="Request error"):
        fetch_remote(url)


def test_fetch_result_from_response():
    url = "https://example.com/config.toml"
    mock_response = httpx.Response(200, content=SAMPLE_CONTENT)
    result = FetchResult.from_response(url, mock_response)

    assert result.checksum == checksum_of_bytes(SAMPLE_CONTENT)
    assert result.content == SAMPLE_CONTENT
