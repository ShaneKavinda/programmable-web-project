"""Root and health check API endpoints."""
from flask import Blueprint, jsonify

root_bp = Blueprint("root", __name__)


@root_bp.route("/")
def index():
    """Root endpoint - API information."""
    return (
        jsonify(
            {
                "name": "Flight Management System API",
                "version": "1.0.0",
                "description": "RESTful API for managing flight bookings",
                "endpoints": {
                    "tokens": {
                        "issue_by_user_id": "/api/users/{user_id}/token",
                        "get_or_update profile": "/api/users/me",
                    },
                    "users": "/api/users/",
                    "flights": {
                        "airports": "/api/flights/airports",
                        "search": "/api/flights/search",
                        "add_or_delete flight": "/api/flights/",
                    },
                    "bookings": {
                        "create_or_list": "/api/bookings/",
                        "detail": "/api/bookings/{booking_id}",
                        "seat_availability": "/api/bookings/availability",
                        "update_status": "/api/bookings/{booking_id}",
                        "cancel": "/api/bookings/{booking_id}",
                    },
                    "swagger": "/apidocs/",
                },
                "documentation": "Visit /apidocs/ for interactive API documentation",
            }
        ),
        200,
    )


@root_bp.route("/health")
def health_check():
    """Health check endpoint."""
    return (
        jsonify(
            {
                "status": "healthy",
                "service": "Flight Management System API",
            }
        ),
        200,
    )
