"""Validate and persist notification events."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from notification_aux.constants import ALLOWED_EVENT_TYPES
from notification_aux.log import logger
from notification_aux.storage import get_conn


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def validate_event_payload(data: dict) -> tuple[bool, str]:
    """Validate incoming event JSON body."""
    required = ["event_type", "booking_id", "user_id", "user_email"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"

    event_type = str(data["event_type"])
    if event_type not in ALLOWED_EVENT_TYPES:
        return False, (
            "Invalid event_type. Must be one of: " + ", ".join(sorted(ALLOWED_EVENT_TYPES))
        )
    return True, ""


def build_delivery_message(event_type: str, booking_id: str) -> str:
    """Create human-readable mock delivery message."""
    suffix = booking_id[:8]
    if event_type == "booking_created":
        return f"Mock email queued: booking #{suffix} created."
    if event_type == "booking_paid":
        return f"Mock email queued: booking #{suffix} payment confirmed."
    return f"Mock email queued: booking #{suffix} cancelled."


def create_event_record(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Validate and persist one notification event."""
    is_valid, message = validate_event_payload(data)
    if not is_valid:
        logger.warning("Rejected event: %s", message)
        return {"error": "Bad Request", "message": message}, 400

    event_id = str(uuid.uuid4())
    event_type = str(data["event_type"])
    booking_id = str(data["booking_id"])
    user_id = str(data["user_id"])
    user_email = str(data["user_email"])
    source = str(data.get("source") or "unknown")
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    occurred_at = str(data.get("occurred_at") or utc_now_iso())
    received_at = utc_now_iso()
    delivery_channel = "mock_email"
    delivery_message = build_delivery_message(event_type, booking_id)
    status = "processed"

    logger.info(
        "Event received: type=%s booking=%s user=%s email=%s source=%s",
        event_type,
        booking_id[:8],
        user_id[:8],
        user_email,
        source,
    )
    logger.info("[MOCK EMAIL -> %s] %s", user_email, delivery_message)

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO notifications (
                id, event_type, booking_id, user_id, user_email, source, payload_json, status,
                delivery_channel, delivery_message, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                event_type,
                booking_id,
                user_id,
                user_email,
                source,
                json.dumps(payload, ensure_ascii=True),
                status,
                delivery_channel,
                delivery_message,
                occurred_at,
                received_at,
            ),
        )

    logger.info("Stored notification event_id=%s status=%s", event_id, status)
    return {
        "event_id": event_id,
        "status": status,
        "delivery_channel": delivery_channel,
        "delivery_message": delivery_message,
    }, 201
