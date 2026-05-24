"""Notifier module: formats and emits drift alerts to stdout (and optionally a webhook)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from driftwatch.checker import DriftResult

logger = logging.getLogger(__name__)


@dataclass
class NotifyResult:
    success: bool
    message: str
    webhook_status_code: Optional[int] = None


def _format_alert(result: DriftResult) -> str:
    """Return a human-readable alert string for a drifted or errored target."""
    ts = datetime.now(timezone.utc).isoformat()
    if result.error:
        return (
            f"[{ts}] ERROR  target={result.target.name!r} "
            f"local={result.target.local_path!r} error={result.error!r}"
        )
    return (
        f"[{ts}] DRIFT  target={result.target.name!r} "
        f"local={result.target.local_path!r} "
        f"remote={result.target.remote_url!r}"
    )


def _build_payload(result: DriftResult) -> dict:
    """Build a JSON-serialisable payload for webhook delivery."""
    return {
        "target": result.target.name,
        "local_path": result.target.local_path,
        "remote_url": result.target.remote_url,
        "drifted": result.drifted,
        "error": result.error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _post_webhook(
    webhook_url: str,
    payload: dict,
    timeout: float,
) -> tuple[bool, Optional[int], Optional[str]]:
    """POST *payload* to *webhook_url* and return (success, status_code, error_message).

    Returns a 3-tuple so that ``notify`` can stay focused on orchestration
    rather than low-level HTTP error handling.
    """
    try:
        response = httpx.post(
            webhook_url,
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        return True, response.status_code, None
    except httpx.HTTPError as exc:
        logger.error("Webhook delivery failed: %s", exc)
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        return False, status_code, str(exc)


def notify(
    result: DriftResult,
    webhook_url: Optional[str] = None,
    timeout: float = 5.0,
) -> NotifyResult:
    """Log the drift result and optionally POST it to a webhook URL."""
    if not (result.drifted or result.error):
        return NotifyResult(success=True, message="no drift, nothing to notify")

    alert_text = _format_alert(result)
    logger.warning(alert_text)
    print(alert_text)

    if not webhook_url:
        return NotifyResult(success=True, message=alert_text)

    payload = _build_payload(result)
    success, status_code, error_message = _post_webhook(webhook_url, payload, timeout)
    if success:
        return NotifyResult(
            success=True,
            message=alert_text,
            webhook_status_code=status_code,
        )
    return NotifyResult(
        success=False,
        message=f"webhook failed: {error_message}",
        webhook_status_code=status_code,
    )
