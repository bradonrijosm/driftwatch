"""Remote content fetcher for DriftWatch."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    url: str
    content: bytes
    status_code: int
    checksum: str

    @classmethod
    def from_response(cls, url: str, response: httpx.Response) -> "FetchResult":
        content = response.content
        checksum = hashlib.sha256(content).hexdigest()
        return cls(
            url=url,
            content=content,
            status_code=response.status_code,
            checksum=checksum,
        )


class FetchError(Exception):
    """Raised when a remote fetch fails."""


def fetch_remote(url: str, timeout: float = 10.0) -> FetchResult:
    """Fetch content from a remote URL and return a FetchResult.

    Raises:
        FetchError: on HTTP errors or connection issues.
    """
    logger.debug("Fetching remote content from %s", url)
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise FetchError(
            f"HTTP {exc.response.status_code} fetching {url}"
        ) from exc
    except httpx.RequestError as exc:
        raise FetchError(f"Request error fetching {url}: {exc}") from exc

    result = FetchResult.from_response(url, response)
    logger.debug("Fetched %d bytes from %s (sha256=%s)", len(result.content), url, result.checksum)
    return result


def checksum_of_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest of *data*."""
    return hashlib.sha256(data).hexdigest()
