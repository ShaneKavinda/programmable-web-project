"""Admin proxy endpoint for notification logs from the auxiliary service."""

from flask import Blueprint, jsonify, request

from ticket_management_system.resources.notification_client import get_aux_notifications
from ticket_management_system.resources.users import admin_required

notification_logs_bp = Blueprint(
    "notification_logs", __name__, url_prefix="/api/aux/notifications"
)


@notification_logs_bp.route("", methods=["GET"])
@admin_required
def notification_logs():
    """Fetch notification logs from auxiliary service."""
    booking_id = request.args.get("booking_id")
    limit_raw = request.args.get("limit", "50")
    try:
        limit = int(limit_raw)
    except ValueError:
        return jsonify({"error": "Bad Request", "message": "limit must be an integer"}), 400

    body, code = get_aux_notifications(booking_id=booking_id, limit=limit)
    return jsonify(body), code
