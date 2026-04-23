"""Booking management API endpoints."""
from flask import Blueprint, jsonify, make_response, request
from marshmallow import ValidationError

from ticket_management_system.static.schema.booking_schemas import (
    BookTicketsSchema,
    PaginationQuerySchema,
    SeatAvailabilityQuerySchema,
    UpdateBookingSchema
)
from ticket_management_system.resources.booking_service import BookingService
from ticket_management_system.resources.notification_client import publish_booking_event
from ticket_management_system.exceptions import (
    FlightNotFoundError,
    SeatUnavailableError,
    BookingNotFoundError,
    BookingConflictError,
    UserNotFoundError,
    TokenExpiredError,
    InvalidTokenError,
    ResourcePermissionError,
)
from ticket_management_system.resources.user_service import UserService
from ticket_management_system.resources.users import (
    ADMIN_API_KEY,
    _attach_refreshed_token,
    token_required,
)

booking_bp = Blueprint("bookings", __name__, url_prefix="/api/bookings")


def _can_access_booking(token_user, booking):
    """Return whether the token user can access the booking."""
    if booking.user_id is None:
        return False
    return booking.user_id == token_user.id


def _booking_forbidden_response():
    """Return a standard booking ownership error response."""
    return jsonify({
        "error": "Forbidden",
        "message": "You do not have permission to access this booking"
    }), 403


def _event_owner_info(booking):
    """Extract user identity for notification events."""
    owner = booking.user
    if owner is not None:
        return str(owner.id), owner.email
    fallback_user_id = str(booking.user_id) if booking.user_id else "unknown"
    return fallback_user_id, "unknown@example.com"


@booking_bp.route("/", methods=["POST"])
def create_booking():
    """Create a new booking for a flight."""
    try:
        schema = BookTicketsSchema()
        data = schema.load(request.get_json())

        booking, _tickets = BookingService.book_tickets(
            user_id=data.get("user_id"),
            flight_id=data["flight_id"],
            passengers=data["passengers"],
            booking_status=data.get("booking_status", "booked")
        )

        response = BookingService.format_booking_detail(booking)
        response["message"] = "Booking created successfully"
        event_user_id, event_user_email = _event_owner_info(booking)
        publish_booking_event(
            event_type="booking_created",
            booking_id=str(booking.id),
            user_id=event_user_id,
            user_email=event_user_email,
            payload={
                "flight_id": str(booking.flight_id),
                "ticket_count": len(booking.tickets),
                "total_price": str(booking.total_price),
                "booking_status": booking.booking_status.name,
            },
        )
        return jsonify(response), 201

    except ValidationError as err:
        return jsonify({
            "error": "Bad Request",
            "message": "Validation failed",
            "errors": err.messages
        }), 400
    except FlightNotFoundError as err:
        return jsonify({
            "error": "Not Found",
            "message": err.message
        }), 404
    except UserNotFoundError as err:
        return jsonify({
            "error": "Not Found",
            "message": err.message
        }), 404
    except SeatUnavailableError as err:
        return jsonify({
            "error": "Conflict",
            "message": err.message
        }), 409
    except BookingConflictError as err:
        return jsonify({
            "error": "Conflict",
            "message": err.message
        }), 409
    except ValueError as err:
        return jsonify({
            "error": "Bad Request",
            "message": str(err)
        }), 400
    except Exception as err:  # pylint: disable=broad-exception-caught
        from ticket_management_system.extensions import db
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(err)
        }), 500


@booking_bp.route("/", methods=["GET"])
@token_required("bookings:read")
def list_bookings(token_user):
    """List bookings."""
    try:
        query_schema = PaginationQuerySchema()
        query_data = query_schema.load(request.args)

        result = BookingService.get_paginated_bookings(
            user_id=token_user.id,
            page=query_data.get("page", 1),
            per_page=query_data.get("per_page", 10)
        )
        return jsonify(result), 200
    except ValidationError as err:
        return jsonify({
            "error": "Bad Request",
            "message": "Validation failed",
            "errors": err.messages
        }), 400
    except Exception as err:  # pylint: disable=broad-exception-caught
        return jsonify({
            "error": "Internal Server Error",
            "message": str(err)
        }), 500


@booking_bp.route("/<uuid:booking_id>", methods=["PUT"])
@token_required("bookings:write")
def update_booking(token_user, booking_id):
    """Update booking status."""
    try:
        booking = BookingService.get_booking_by_id(booking_id)
        if not booking:
            raise BookingNotFoundError(booking_id)
        if not _can_access_booking(token_user, booking):
            return _booking_forbidden_response()

        schema = UpdateBookingSchema()
        data = schema.load(request.get_json())

        updated_booking = BookingService.update_booking(
            booking_id=booking_id,
            booking_status=data["booking_status"]
        )

        response = BookingService.format_booking_detail(updated_booking)
        response["message"] = "Booking updated successfully"
        return jsonify(response), 200

    except ValidationError as err:
        return jsonify({
            "error": "Bad Request",
            "message": "Validation failed",
            "errors": err.messages
        }), 400
    except BookingNotFoundError as err:
        return jsonify({
            "error": "Not Found",
            "message": err.message
        }), 404
    except BookingConflictError as err:
        return jsonify({
            "error": "Conflict",
            "message": err.message
        }), 409
    except ValueError as err:
        return jsonify({
            "error": "Bad Request",
            "message": str(err)
        }), 400
    except Exception as err:  # pylint: disable=broad-exception-caught
        from ticket_management_system.extensions import db
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(err)
        }), 500


@booking_bp.route("/<uuid:booking_id>", methods=["DELETE"])
def cancel_booking(booking_id):
    """Cancel a booking.

    Owners send ``Authorization: Bearer`` with ``bookings:write`` scope.
    Admins send ``x-api-key`` matching ``ADMIN_API_KEY`` to cancel any user's booking.
    """
    api_key = request.headers.get("x-api-key", "").strip()
    admin_cancel = False
    token_user = None

    if api_key:
        if api_key != ADMIN_API_KEY:
            return jsonify({
                "error": "Forbidden",
                "message": "Invalid API key",
            }), 403
        admin_cancel = True
    else:
        token = None
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            try:
                token_type, token = auth_header.split(" ", 1)
                if token_type.lower() != "bearer":
                    raise ValueError
            except ValueError:
                return jsonify({
                    "error": "Invalid authorization header format",
                    "message": "Use format: Bearer <token>",
                }), 401
        if not token:
            return jsonify({
                "error": "Authentication required",
                "message": "Provide x-api-key (admin) or Bearer token (owner)",
            }), 401
        try:
            token_user = UserService.verify_token(
                token,
                required_resource="bookings:write",
            )
        except TokenExpiredError as err:
            return jsonify({
                "error": "Token expired",
                "message": err.message,
            }), 401
        except ResourcePermissionError as err:
            return jsonify({
                "error": "Forbidden",
                "message": err.message,
            }), 403
        except (InvalidTokenError, UserNotFoundError) as err:
            return jsonify({
                "error": "Invalid token",
                "message": err.message,
            }), 401

    try:
        booking = BookingService.get_booking_by_id(booking_id)
        if not booking:
            raise BookingNotFoundError(booking_id)
        if not admin_cancel and not _can_access_booking(token_user, booking):
            return _booking_forbidden_response()

        cancelled_booking = BookingService.cancel_booking(booking_id)

        response = BookingService.format_booking_detail(cancelled_booking)
        response["message"] = "Booking cancelled successfully"
        event_user_id, event_user_email = _event_owner_info(cancelled_booking)
        publish_booking_event(
            event_type="booking_cancelled",
            booking_id=str(cancelled_booking.id),
            user_id=event_user_id,
            user_email=event_user_email,
            payload={
                "flight_id": str(cancelled_booking.flight_id),
                "total_price": str(cancelled_booking.total_price),
                "booking_status": cancelled_booking.booking_status.name,
            },
        )
        body = jsonify(response)
        if admin_cancel:
            return body, 200
        resp = make_response(body, 200)
        return _attach_refreshed_token(resp, token_user)

    except BookingNotFoundError as err:
        return jsonify({
            "error": "Not Found",
            "message": err.message
        }), 404
    except BookingConflictError as err:
        return jsonify({
            "error": "Conflict",
            "message": err.message
        }), 409
    except Exception as err:  # pylint: disable=broad-exception-caught
        from ticket_management_system.extensions import db
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(err)
        }), 500


@booking_bp.route("/<uuid:booking_id>", methods=["GET"])
@token_required("bookings:read")
def get_booking(token_user, booking_id):
    """Get booking details by ID."""
    try:
        booking = BookingService.get_booking_by_id(booking_id)
        if not booking:
            raise BookingNotFoundError(booking_id)
        if not _can_access_booking(token_user, booking):
            return _booking_forbidden_response()

        return jsonify(BookingService.format_booking_detail(booking)), 200

    except BookingNotFoundError as err:
        return jsonify({
            "error": "Not Found",
            "message": err.message
        }), 404
    except Exception as err:  # pylint: disable=broad-exception-caught
        return jsonify({
            "error": "Internal Server Error",
            "message": str(err)
        }), 500


@booking_bp.route("/availability", methods=["GET"])
def get_seat_availability():
    """Check seat availability."""
    try:
        schema = SeatAvailabilityQuerySchema()
        data = schema.load(request.args)
        seat_num = data["seat_num"]
        available = BookingService.get_seat_availability(
            flight_id=data["flight_id"],
            seat_num=seat_num
        )
        return jsonify({
            "flight_id": str(data["flight_id"]),
            "seat_num": seat_num.strip().upper(),
            "available": available
        }), 200

    except ValidationError as err:
        return jsonify({
            "error": "Bad Request",
            "message": "Validation failed",
            "errors": err.messages
        }), 400
    except ValueError as err:
        return jsonify({
            "error": "Bad Request",
            "message": str(err)
        }), 400
    except Exception as err:  # pylint: disable=broad-exception-caught
        return jsonify({
            "error": "Internal Server Error",
            "message": str(err)
        }), 500
