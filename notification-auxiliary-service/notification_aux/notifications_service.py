"""Read notification rows from SQLite."""

from __future__ import annotations

import json
from typing import Any

from notification_aux.storage import get_conn


def _row_to_item(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "event_type": row["event_type"],
        "booking_id": row["booking_id"],
        "user_id": row["user_id"],
        "user_email": row["user_email"],
        "source": row["source"],
        "status": row["status"],
        "delivery_channel": row["delivery_channel"],
        "delivery_message": row["delivery_message"],
        "payload": json.loads(row["payload_json"]),
        "occurred_at": row["occurred_at"],
        "received_at": row["received_at"],
    }


def list_notifications_data(booking_id: str | None, limit: int) -> tuple[dict[str, Any], int]:
    """List notification rows with filter and limit."""
    if limit < 1 or limit > 200:
        return {"error": "Bad Request", "message": "limit must be between 1 and 200"}, 400

    with get_conn() as conn:
        if booking_id:
            rows = conn.execute(
                """
                SELECT * FROM notifications
                WHERE booking_id = ?
                ORDER BY received_at DESC
                LIMIT ?
                """,
                (booking_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM notifications
                ORDER BY received_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    items = [_row_to_item(row) for row in rows]
    return {"notifications": items, "count": len(items)}, 200


def fetch_notification_payload(event_id: str) -> tuple[dict[str, Any] | None, int]:
    """Return ({'notification': ...}, 200) or (None, 404)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM notifications WHERE id = ?",
            (event_id,),
        ).fetchone()

    if row is None:
        return None, 404
    return {"notification": _row_to_item(row)}, 200
