"""Client helper for the notification auxiliary service (REST)."""

from __future__ import annotations

import os
from typing import Any

import requests


def _base_url() -> str:
    return os.getenv("NOTIFICATION_AUX_BASE_URL", "").strip().rstrip("/")


def _timeout_seconds() -> float:
    raw = os.getenv("NOTIFICATION_AUX_TIMEOUT_SEC", "1.5").strip()
    try:
        return max(float(raw), 0.1)
    except ValueError:
        return 1.5


def publish_booking_event(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    event_type: str,
    booking_id: str,
    user_id: str,
    user_email: str,
    *,
    source: str = "ticket_management_system_api",
    payload: dict[str, Any] | None = None,
) -> bool:
    """
    Publish a booking-related event to auxiliary notification service.

    Best-effort: failures do not break primary API operations.
    """
    base_url = _base_url()
    if not base_url:
        return False

    body = {
        "event_type": event_type,
        "booking_id": booking_id,
        "user_id": user_id,
        "user_email": user_email,
        "source": source,
        "payload": payload or {},
    }

    try:
        response = requests.post(
            f"{base_url}/api/events",
            json=body,
            timeout=_timeout_seconds(),
        )
        return response.status_code < 500
    except requests.RequestException:
        return False


def get_aux_notifications(
    booking_id: str | None = None, limit: int = 50
) -> tuple[dict[str, Any], int]:
    """Fetch notification logs from auxiliary service."""
    normalized_limit = max(1, min(limit, 200))
    base_url = _base_url()
    if not base_url:
        return {
            "error": "Service Unavailable",
            "message": "NOTIFICATION_AUX_BASE_URL is not configured",
        }, 503

    params: dict[str, str | int] = {"limit": normalized_limit}
    if booking_id:
        params["booking_id"] = booking_id

    try:
        response = requests.get(
            f"{base_url}/api/notifications",
            params=params,
            timeout=max(_timeout_seconds(), 3.0),
        )
        return response.json(), response.status_code
    except requests.RequestException as exc:
        return {
            "error": "Service Unavailable",
            "message": f"Could not reach auxiliary service: {exc}",
        }, 503
