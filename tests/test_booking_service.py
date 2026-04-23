"""
Unit tests for BookingService class.
Tests booking business logic and helper methods.
"""

from datetime import datetime
from decimal import Decimal
import uuid

import pytest

from ticket_management_system.exceptions import (
    BookingConflictError,
    FlightNotFoundError,
    SeatUnavailableError,
)
from ticket_management_system.extensions import db
from ticket_management_system.models import BookingStatus, Flight, FlightStatus, SeatClass, User
from ticket_management_system.resources.booking_service import BookingService


@pytest.fixture
def booking_user(app):
    """Create a dedicated user for booking service tests."""
    with app.app_context():
        user = User(
            firstname="Booking",
            lastname="Tester",
            email="booking.service@test.com",
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        user_id = user.id

        yield user

        user = db.session.get(User, user_id)
        if user:
            db.session.delete(user)
            db.session.commit()


def _create_flight(
    code="BK101",
    status=FlightStatus.active,
    base_price=Decimal("200.00")
):
    """Create an in-memory flight object."""
    return Flight(
        flight_code=code,
        origin_airport="JFK",
        destination_airport="LAX",
        departure_time=datetime(2026, 4, 1, 10, 0),
        arrival_time=datetime(2026, 4, 1, 14, 0),
        base_price=base_price,
        status=status
    )


class TestBookingServiceBookTickets:
    """Test ticket booking workflow."""

    def test_book_tickets_success_single_passenger(self, app, booking_user):
        """Book one ticket successfully."""
        with app.app_context():
            flight = _create_flight(code="BK111", base_price=Decimal("250.00"))
            db.session.add(flight)
            db.session.commit()

            booking, tickets = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "John Doe",
                        "passenger_passport_num": "P12345678",
                        "seat_num": "12a",
                        "seat_class": "economy"
                    }
                ]
            )

            assert booking.id is not None
            assert booking.flight_id == flight.id
            assert booking.user_id == booking_user.id
            assert booking.booking_status == BookingStatus.booked
            assert str(booking.total_price) == "250.00"
            assert len(tickets) == 1
            assert tickets[0].seat_num == "12A"

            db.session.delete(flight)
            db.session.commit()

    def test_book_tickets_success_multiple_passengers_total_price(self, app, booking_user):
        """Book multiple tickets and verify aggregated total."""
        with app.app_context():
            flight = _create_flight(code="BK112", base_price=Decimal("100.00"))
            db.session.add(flight)
            db.session.commit()

            booking, tickets = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Alice",
                        "passenger_passport_num": "A12345678",
                        "seat_num": "1A",
                        "seat_class": "economy"
                    },
                    {
                        "passenger_name": "Bob",
                        "passenger_passport_num": "B12345678",
                        "seat_num": "1B",
                        "seat_class": "business"
                    }
                ]
            )

            assert len(tickets) == 2
            assert str(booking.total_price) == "350.00"

            db.session.delete(flight)
            db.session.commit()

    def test_book_tickets_requires_email_when_no_user_id(self, app):
        """Anonymous service bookings require first passenger email for ownership."""
        with app.app_context():
            flight = _create_flight(code="BK113")
            db.session.add(flight)
            db.session.commit()

            with pytest.raises(ValueError, match="First passenger email is required"):
                BookingService.book_tickets(
                    user_id=None,
                    flight_id=flight.id,
                    passengers=[
                        {
                            "passenger_name": "No Email",
                            "passenger_passport_num": "N12345678",
                            "seat_num": "2A",
                            "seat_class": "economy"
                        }
                    ]
                )

            db.session.delete(flight)
            db.session.commit()

    def test_book_tickets_flight_not_found(self, app, booking_user):
        """Raise FlightNotFoundError for non-existent flight."""
        with app.app_context():
            with pytest.raises(FlightNotFoundError):
                BookingService.book_tickets(
                    user_id=booking_user.id,
                    flight_id=uuid.uuid4(),
                    passengers=[
                        {
                            "passenger_name": "John Doe",
                            "passenger_passport_num": "P12345678",
                            "seat_num": "12A",
                            "seat_class": "economy"
                        }
                    ]
                )

    def test_book_tickets_rejects_duplicate_seat_in_same_request(self, app, booking_user):
        """Reject duplicate seat numbers in a single booking payload."""
        with app.app_context():
            flight = _create_flight(code="BK113")
            db.session.add(flight)
            db.session.commit()

            with pytest.raises(SeatUnavailableError):
                BookingService.book_tickets(
                    user_id=booking_user.id,
                    flight_id=flight.id,
                    passengers=[
                        {
                            "passenger_name": "Alice",
                            "passenger_passport_num": "A12345678",
                            "seat_num": "2A",
                            "seat_class": "economy"
                        },
                        {
                            "passenger_name": "Bob",
                            "passenger_passport_num": "B12345678",
                            "seat_num": "2a",
                            "seat_class": "economy"
                        }
                    ]
                )

            db.session.delete(flight)
            db.session.commit()

    def test_book_tickets_rejects_non_bookable_flight_status(self, app, booking_user):
        """Reject booking for cancelled/non-bookable flights."""
        with app.app_context():
            flight = _create_flight(code="BK114", status=FlightStatus.cancelled)
            db.session.add(flight)
            db.session.commit()

            with pytest.raises(BookingConflictError):
                BookingService.book_tickets(
                    user_id=booking_user.id,
                    flight_id=flight.id,
                    passengers=[
                        {
                            "passenger_name": "John Doe",
                            "passenger_passport_num": "P12345678",
                            "seat_num": "10A",
                            "seat_class": "economy"
                        }
                    ]
                )

            db.session.delete(flight)
            db.session.commit()


class TestBookingServiceHelpers:
    """Test helper methods and pagination helpers."""

    def test_calculate_ticket_price_by_seat_class(self):
        """Calculate class multipliers correctly."""
        assert BookingService.calculate_ticket_price(Decimal("100.00"), SeatClass.economy) == Decimal("100.00")
        assert BookingService.calculate_ticket_price(Decimal("100.00"), SeatClass.business) == Decimal("250.00")
        assert BookingService.calculate_ticket_price(Decimal("100.00"), SeatClass.first) == Decimal("400.00")

    def test_get_seat_availability_true_then_false(self, app, booking_user):
        """Seat availability changes after booking."""
        with app.app_context():
            flight = _create_flight(code="BK115")
            db.session.add(flight)
            db.session.commit()

            available_before = BookingService.get_seat_availability(flight.id, "15C")
            assert available_before is True

            BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Seat Owner",
                        "passenger_passport_num": "S12345678",
                        "seat_num": "15c",
                        "seat_class": "economy"
                    }
                ]
            )

            available_after = BookingService.get_seat_availability(flight.id, "15C")
            assert available_after is False

            db.session.delete(flight)
            db.session.commit()

    def test_get_paginated_bookings_filtered_by_user(self, app, booking_user):
        """Paginated listing can be filtered by user id."""
        with app.app_context():
            flight1 = _create_flight(code="BK116")
            flight2 = _create_flight(code="BK117")
            db.session.add(flight1)
            db.session.add(flight2)
            db.session.commit()

            BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight1.id,
                passengers=[
                    {
                        "passenger_name": "One",
                        "passenger_passport_num": "P11111111",
                        "seat_num": "3A",
                        "seat_class": "economy"
                    }
                ]
            )
            BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight2.id,
                passengers=[
                    {
                        "passenger_name": "Two",
                        "passenger_passport_num": "P22222222",
                        "seat_num": "4A",
                        "seat_class": "economy"
                    }
                ]
            )

            result = BookingService.get_paginated_bookings(user_id=booking_user.id, page=1, per_page=1)

            assert "bookings" in result
            assert "pagination" in result
            assert len(result["bookings"]) == 1
            assert result["pagination"]["page"] == 1
            assert result["pagination"]["per_page"] == 1
            assert result["pagination"]["total_items"] >= 2

            db.session.delete(flight1)
            db.session.delete(flight2)
            db.session.commit()


class TestBookingServiceUpdateBooking:
    """Test update_booking method."""

    def test_update_booking_success_booked_to_paid(self, app, booking_user):
        """Successfully update booking status from booked to paid."""
        with app.app_context():
            flight = _create_flight(code="BK120")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P30303030",
                        "seat_num": "5A",
                        "seat_class": "economy"
                    }
                ]
            )

            original_updated_at = booking.updated_at

            # Update booking
            updated_booking = BookingService.update_booking(
                booking_id=booking.id,
                booking_status="paid"
            )

            assert updated_booking is not None
            assert updated_booking.booking_status == BookingStatus.paid
            assert updated_booking.id == booking.id
            assert updated_booking.updated_at > original_updated_at

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_booked_to_cancelled(self, app, booking_user):
        """Update booking from booked to cancelled."""
        with app.app_context():
            flight = _create_flight(code="BK121")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P31313131",
                        "seat_num": "6A",
                        "seat_class": "economy"
                    }
                ]
            )

            updated_booking = BookingService.update_booking(
                booking_id=booking.id,
                booking_status=BookingStatus.cancelled
            )

            assert updated_booking.booking_status == BookingStatus.cancelled

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_paid_to_refunded(self, app, booking_user):
        """Update booking from paid to refunded."""
        with app.app_context():
            flight = _create_flight(code="BK122")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P32323232",
                        "seat_num": "7A",
                        "seat_class": "economy"
                    }
                ],
                booking_status=BookingStatus.paid
            )

            updated_booking = BookingService.update_booking(
                booking_id=booking.id,
                booking_status="refunded"
            )

            assert updated_booking.booking_status == BookingStatus.refunded

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_cannot_update_cancelled(self, app, booking_user):
        """Cannot update a booking that is already cancelled."""
        with app.app_context():
            flight = _create_flight(code="BK123")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P33333333",
                        "seat_num": "8A",
                        "seat_class": "economy"
                    }
                ],
                booking_status=BookingStatus.cancelled
            )

            with pytest.raises(BookingConflictError) as exc_info:
                BookingService.update_booking(
                    booking_id=booking.id,
                    booking_status="paid"
                )

            assert "cannot update" in str(exc_info.value).lower()
            assert "cancelled" in str(exc_info.value).lower()

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_cannot_update_refunded(self, app, booking_user):
        """Cannot update a booking that is already refunded."""
        with app.app_context():
            flight = _create_flight(code="BK124")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P34343434",
                        "seat_num": "9A",
                        "seat_class": "economy"
                    }
                ],
                booking_status=BookingStatus.refunded
            )

            with pytest.raises(BookingConflictError) as exc_info:
                BookingService.update_booking(
                    booking_id=booking.id,
                    booking_status="paid"
                )

            assert "cannot update" in str(exc_info.value).lower()
            assert "refunded" in str(exc_info.value).lower()

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_with_none_status_raises_error(self, app, booking_user):
        """Passing None as booking_status raises ValueError."""
        with app.app_context():
            flight = _create_flight(code="BK125")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P35353535",
                        "seat_num": "10A",
                        "seat_class": "economy"
                    }
                ]
            )

            with pytest.raises(ValueError) as exc_info:
                BookingService.update_booking(
                    booking_id=booking.id,
                    booking_status=None
                )

            assert "required" in str(exc_info.value).lower()

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_invalid_status_raises_error(self, app, booking_user):
        """Invalid booking status raises ValueError."""
        with app.app_context():
            flight = _create_flight(code="BK126")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P36363636",
                        "seat_num": "11A",
                        "seat_class": "economy"
                    }
                ]
            )

            with pytest.raises(ValueError):
                BookingService.update_booking(
                    booking_id=booking.id,
                    booking_status="invalid_status"
                )

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_not_found_except_BookingNotFoundError(self, app):
        """Updating non-existent booking raises BookingNotFoundError."""
        with app.app_context():
            from ticket_management_system.exceptions import BookingNotFoundError

            fake_booking_id = uuid.uuid4()
            with pytest.raises(BookingNotFoundError) as exc_info:
                BookingService.update_booking(
                    booking_id=fake_booking_id,
                    booking_status="paid"
                )

            assert exc_info.value.booking_id == fake_booking_id
            assert "not found" in exc_info.value.message.lower()

    def test_update_booking_updates_timestamp(self, app, booking_user):
        """Updating a booking updates the updated_at timestamp."""
        with app.app_context():
            flight = _create_flight(code="BK127")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P37373737",
                        "seat_num": "12A",
                        "seat_class": "economy"
                    }
                ]
            )

            original_updated_at = booking.updated_at

            import time
            time.sleep(0.1)

            updated_booking = BookingService.update_booking(
                booking_id=booking.id,
                booking_status="paid"
            )

            assert updated_booking.updated_at > original_updated_at

            db.session.delete(flight)
            db.session.commit()


class TestBookingServiceCancelBooking:
    """Test cancel_booking method."""

    def test_cancel_booking_success_from_booked(self, app, booking_user):
        """Successfully cancel a booked booking."""
        with app.app_context():
            flight = _create_flight(code="BK130")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P40404040",
                        "seat_num": "13A",
                        "seat_class": "economy"
                    }
                ]
            )

            original_updated_at = booking.updated_at

            cancelled_booking = BookingService.cancel_booking(booking.id)

            assert cancelled_booking is not None
            assert cancelled_booking.booking_status == BookingStatus.cancelled
            assert cancelled_booking.id == booking.id
            assert cancelled_booking.updated_at > original_updated_at

            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_success_from_paid(self, app, booking_user):
        """Successfully cancel a paid booking."""
        with app.app_context():
            flight = _create_flight(code="BK131")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P41414141",
                        "seat_num": "14A",
                        "seat_class": "economy"
                    }
                ],
                booking_status=BookingStatus.paid
            )

            cancelled_booking = BookingService.cancel_booking(booking.id)

            assert cancelled_booking.booking_status == BookingStatus.cancelled

            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_already_cancelled(self, app, booking_user):
        """Cannot cancel a booking that is already cancelled."""
        with app.app_context():
            flight = _create_flight(code="BK132")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P42424242",
                        "seat_num": "15A",
                        "seat_class": "economy"
                    }
                ],
                booking_status=BookingStatus.cancelled
            )

            with pytest.raises(BookingConflictError) as exc_info:
                BookingService.cancel_booking(booking.id)

            assert "already cancelled" in str(exc_info.value).lower()

            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_cannot_cancel_refunded(self, app, booking_user):
        """Cannot cancel a booking that is refunded."""
        with app.app_context():
            flight = _create_flight(code="BK133")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P43434343",
                        "seat_num": "16A",
                        "seat_class": "economy"
                    }
                ],
                booking_status=BookingStatus.refunded
            )

            with pytest.raises(BookingConflictError) as exc_info:
                BookingService.cancel_booking(booking.id)

            assert "cannot cancel" in str(exc_info.value).lower()
            assert "refunded" in str(exc_info.value).lower()

            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_not_found_raises_exception(self, app):
        """Cancelling non-existent booking raises BookingNotFoundError."""
        with app.app_context():
            from ticket_management_system.exceptions import BookingNotFoundError

            fake_booking_id = uuid.uuid4()
            with pytest.raises(BookingNotFoundError) as exc_info:
                BookingService.cancel_booking(fake_booking_id)

            assert exc_info.value.booking_id == fake_booking_id
            assert "not found" in exc_info.value.message.lower()

    def test_cancel_booking_updates_timestamp(self, app, booking_user):
        """Cancelling a booking updates the updated_at timestamp."""
        with app.app_context():
            flight = _create_flight(code="BK134")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P44444444",
                        "seat_num": "17A",
                        "seat_class": "economy"
                    }
                ]
            )

            original_updated_at = booking.updated_at

            import time
            time.sleep(0.1)

            cancelled_booking = BookingService.cancel_booking(booking.id)

            assert cancelled_booking.updated_at > original_updated_at

            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_maintains_other_fields(self, app, booking_user):
        """Cancelling a booking only changes status, not other fields."""
        with app.app_context():
            flight = _create_flight(code="BK135")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=booking_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test User",
                        "passenger_passport_num": "P45454545",
                        "seat_num": "18A",
                        "seat_class": "economy"
                    }
                ]
            )

            original_total_price = booking.total_price
            original_user_id = booking.user_id
            original_flight_id = booking.flight_id

            cancelled_booking = BookingService.cancel_booking(booking.id)

            assert cancelled_booking.total_price == original_total_price
            assert cancelled_booking.user_id == original_user_id
            assert cancelled_booking.flight_id == original_flight_id

            db.session.delete(flight)
            db.session.commit()

