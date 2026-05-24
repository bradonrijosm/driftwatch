"""Webhook notifier with optional rate-limiting."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests

from driftwatch.checker import DriftResult
from driftwatch.config import WatchTarget
from driftwatch.rate_limiter import RateLimiter

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotifyResult:
    target_name: str
    sent: bool
    rate_limited: bool = False
    status_code: Optional[int] = None
    error: Optional[str] = None


def _format_alert(target: WatchTarget, result: DriftResult) -> str:
    if result.error:
        return f"[ERROR] {target.name}: {result.error}"
    return (
        f"[DRIFT] {target.name}: local checksum {result.local_checksum!r} "
        f"!= remote checksum {result.remote_checksum!r}"
    )


def _build_payload(target: WatchTarget, result: DriftResult) -> dict:
    return {
        "text": _format_alert(target, result),
        "target": target.name,
        "local_path": target.local_path,
        "remote_url": target.remote_url,
        "drifted": result.drifted,
        "error": result.error,
    }


def _post_webhook(url: str, payload: dict, timeout: int = 10) -> int:
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.status_code


def notify(
    target: WatchTarget,
    result: DriftResult,
    webhook_url: str,
    *,
    rate_limiter: Optional[RateLimiter] = None,
) -> NotifyResult:
    """Send a webhook notification for a drifted or errored target.

    If *rate_limiter* is provided and the bucket is exhausted the
    notification is silently suppressed and ``rate_limited=True`` is
    returned.
    """
    if not result.drifted and not result.error:
        return NotifyResult(target_name=target.name, sent=False)

    if rate_limiter is not None and not rate_limiter.acquire():
        log.warning("Rate-limited notification for %s", target.name)
        return NotifyResult(target_name=target.name, sent=False, rate_limited=True)

    payload = _build_payload(target, result)
    try:
        code = _post_webhook(webhook_url, payload)
        log.info("Notified webhook for %s (HTTP %s)", target.name, code)
        return NotifyResult(target_name=target.name, sent=True, status_code=code)
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else None
        log.error("Webhook HTTP error for %s: %s", target.name, exc)
        return NotifyResult(target_name=target.name, sent=False, status_code=code, error=str(exc))
    except requests.RequestException as exc:
        log.error("Webhook request failed for %s: %s", target.name, exc)
        return NotifyResult(target_name=target.name, sent=False, error=str(exc))
