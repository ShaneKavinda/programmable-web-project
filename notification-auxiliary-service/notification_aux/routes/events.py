"""Inbound event webhook from main API."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from notification_aux.events_service import create_event_record

bp = Blueprint("events", __name__)


@bp.post("/api/events")
def create_event():
    """Receive an event from main API and persist notification record."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Bad Request", "message": "Request body must be JSON"}), 400
    body, code = create_event_record(data)
    return jsonify(body), code
