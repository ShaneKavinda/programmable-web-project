"""Notification log listing and detail."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from notification_aux.notifications_service import fetch_notification_payload, list_notifications_data

bp = Blueprint("notifications", __name__)


@bp.get("/api/notifications")
def list_notifications():
    """List notifications with optional booking filter."""
    booking_id = request.args.get("booking_id")
    limit_raw = request.args.get("limit", "50")
    try:
        limit = min(max(int(limit_raw), 1), 200)
    except ValueError:
        return jsonify({"error": "Bad Request", "message": "limit must be an integer"}), 400
    body, code = list_notifications_data(booking_id, limit)
    return jsonify(body), code


@bp.get("/api/notifications/<event_id>")
def get_notification(event_id: str):
    """Get one notification by event id."""
    body, code = fetch_notification_payload(event_id)
    if code == 404:
        return jsonify({"error": "Not Found", "message": "Notification not found"}), 404
    return jsonify(body), 200
