"""
Payment routes for the Flight Management System API.
Provides endpoint for booking payment and confirmation.
"""

from flask import Blueprint, request, jsonify
import uuid
from ticket_management_system.extensions import db
from ticket_management_system.models import Booking, BookingStatus
from ticket_management_system.resources.notification_client import publish_booking_event
from ticket_management_system.resources.users import token_required

payment_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

@payment_bp.route('/', methods=['POST'])
@token_required('payments:create')
def process_payment(token_user):  # pylint: disable=too-many-return-statements
    """
    Process payment for a booking and confirm it.

    This function requires user input for: booking_number, credit_card_number and security_code

    Properties:
        id:
            type: string
            example: "e8f63a4b-0410-4797-bb76-fe389098d18f"
        credit_card_number:
            type: string
            example: "1234567812345678"
        security_code:
            type: string
            example: "123"
    This function returns:
      200 if payment successful and booking confirmed
      400 if invalid input
      404 if booking not found
      409 if trying to pay for a booking that's already been paid
    """

    try:
        data = request.get_json(force=True, silent=True)

        if not data:
            return jsonify({
                "error": "Bad Request",
                "message": "Request body must be JSON"
            }), 400

        id = data.get("booking_number")
        credit_card_number = data.get("credit_card_number")
        security_code = data.get("security_code")

        if not id or not credit_card_number or not security_code:
            return jsonify({
                "error": "Bad Request",
                "message": "All fields are required"
            }), 400

        if not (credit_card_number.isdigit() and len(credit_card_number) == 16):
            return jsonify({
                "error": "Bad Request",
                "message": "Credit card number must be 16 digits"
            }), 400

        if not (security_code.isdigit() and len(security_code) == 3):
            return jsonify({
                "error": "Bad Request",
                "message": "Security code must be 3 digits"
            }), 400

        # Convert booking_number string to UUID
        try:
            booking_uuid = uuid.UUID(id)
        except (ValueError, AttributeError):
            return jsonify({
                "error": "Bad Request",
                "message": "Invalid booking ID format"
            }), 400

        # Find booking
        booking = Booking.query.filter_by(id=booking_uuid).first()

        if not booking:
            return jsonify({
                "error": "Not Found",
                "message": "Booking not found"
            }), 404

        # Ensure booking belongs to user
        if booking.user_id != token_user.id:
            return jsonify({
                "error": "Forbidden",
                "message": "You cannot pay for another user's booking"
            }), 403

        # Prevent double payment
        if booking.booking_status == BookingStatus.paid:
            return jsonify({
                "error": "Conflict",
                "message": "Booking is already paid"
            }), 409

        booking.booking_status = BookingStatus.paid

        db.session.commit()
        publish_booking_event(
            event_type="booking_paid",
            booking_id=str(booking.id),
            user_id=str(token_user.id),
            user_email=token_user.email,
            payload={
                "flight_id": str(booking.flight_id),
                "total_price": str(booking.total_price),
                "booking_status": booking.booking_status.name,
            },
        )

        return jsonify({
            "message": "Payment successful. Booking confirmed.",
            "booking_number": str(booking.id),
            "status": booking.booking_status.name
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500
