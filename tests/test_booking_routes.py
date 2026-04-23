"""
Unit tests for booking route endpoints.
Tests create/list/detail/availability workflows.
"""

import os
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import quote

from ticket_management_system.extensions import db
from ticket_management_system.models import Flight, FlightStatus, User
from ticket_management_system.resources.booking_service import BookingService


def _create_test_flight(code="RT101", status=FlightStatus.active, base_price=Decimal("300.00")):
    """Build a flight object for route tests."""
    return Flight(
        flight_code=code,
        origin_airport="JFK",
        destination_airport="LAX",
        departure_time=datetime(2026, 5, 1, 10, 0),
        arrival_time=datetime(2026, 5, 1, 14, 0),
        base_price=base_price,
        status=status
    )


class TestCreateBookingEndpoint:
    """Test POST /api/bookings/ endpoint."""

    def test_create_booking_success(self, client, app, test_user, sample_flights):
        """Create booking with one passenger and assign by existing email."""
        with app.app_context():
            response = client.post(
                "/api/bookings/",
                json={
                    "flight_id": str(sample_flights[0].id),
                    "passengers": [
                        {
                            "passenger_name": "John Doe",
                            "email": test_user.email,
                            "passenger_passport_num": "P12345678",
                            "seat_num": "12A",
                            "seat_class": "economy"
                        }
                    ]
                }
            )

            assert response.status_code == 201
            data = response.get_json()
            assert data["message"] == "Booking created successfully"
            assert "booking" in data
            assert data["booking"]["user_id"] == str(test_user.id)
            assert data["booking"]["flight_id"] == str(sample_flights[0].id)
            assert len(data["booking"]["tickets"]) == 1

    def test_create_booking_invalid_payload(self, client, auth_headers):
        """Validation error for missing required fields."""
        response = client.post(
            "/api/bookings/",
            headers=auth_headers,
            json={"passengers": []}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "Bad Request"
        assert "errors" in data

    def test_create_booking_flight_not_found(self, client, auth_headers):
        """Return 404 when target flight does not exist."""
        response = client.post(
            "/api/bookings/",
            headers=auth_headers,
            json={
                "flight_id": "fe4a1338-4b98-4b51-9f5c-1234567890ab",
                "passengers": [
                    {
                        "passenger_name": "John Doe",
                        "email": "missing.flight.owner@test.com",
                        "passenger_passport_num": "P12345678",
                        "seat_num": "12A",
                        "seat_class": "economy"
                    }
                ]
            }
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Not Found"

    def test_create_booking_seat_already_taken(self, client, app, auth_headers):
        """Return 409 when booking an already reserved seat."""
        with app.app_context():
            flight = _create_test_flight(code="RT102")
            db.session.add(flight)
            db.session.commit()

            first = client.post(
                "/api/bookings/",
                headers=auth_headers,
                json={
                    "flight_id": str(flight.id),
                    "passengers": [
                        {
                            "passenger_name": "Passenger One",
                            "email": "passenger.one@test.com",
                            "passenger_passport_num": "P11111111",
                            "seat_num": "1A",
                            "seat_class": "economy"
                        }
                    ]
                }
            )
            assert first.status_code == 201

            second = client.post(
                "/api/bookings/",
                headers=auth_headers,
                json={
                    "flight_id": str(flight.id),
                    "passengers": [
                        {
                            "passenger_name": "Passenger Two",
                            "email": "passenger.two@test.com",
                            "passenger_passport_num": "P22222222",
                            "seat_num": "1A",
                            "seat_class": "economy"
                        }
                    ]
                }
            )
            assert second.status_code == 409
            data = second.get_json()
            assert data["error"] == "Conflict"

            db.session.delete(flight)
            db.session.commit()

    def test_create_booking_without_auth_creates_user_from_email(self, client, app, sample_flights):
        """Unauthenticated clients can create bookings with a receipt email."""
        owner_email = "new.booking.owner@test.com"
        response = client.post(
            "/api/bookings/",
            json={
                "flight_id": str(sample_flights[0].id),
                "passengers": [
                    {
                        "passenger_name": "John Doe",
                        "email": owner_email,
                        "passenger_passport_num": "P12345678",
                        "seat_num": "12A",
                        "seat_class": "economy"
                    }
                ]
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["message"] == "Booking created successfully"
        assert data["booking"]["flight_id"] == str(sample_flights[0].id)
        assert data["booking"]["user_id"] is not None

        with app.app_context():
            owner = User.query.filter_by(email=owner_email).first()
            assert owner is not None
            assert data["booking"]["user_id"] == str(owner.id)

    def test_create_booking_requires_first_passenger_email(self, client, sample_flights):
        """The first passenger email is required for booking ownership."""
        response = client.post(
            "/api/bookings/",
            json={
                "flight_id": str(sample_flights[0].id),
                "passengers": [
                    {
                        "passenger_name": "John Doe",
                        "passenger_passport_num": "P12345678",
                        "seat_num": "12A",
                        "seat_class": "economy"
                    }
                ]
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "Bad Request"
        assert "passengers" in data["errors"]

    def test_create_booking_later_passenger_email_does_not_satisfy_owner_email(
        self, client, sample_flights
    ):
        """Only passengers[0].email satisfies the booking owner email requirement."""
        response = client.post(
            "/api/bookings/",
            json={
                "flight_id": str(sample_flights[0].id),
                "passengers": [
                    {
                        "passenger_name": "First Passenger",
                        "passenger_passport_num": "P12345678",
                        "seat_num": "12A",
                        "seat_class": "economy"
                    },
                    {
                        "passenger_name": "Second Passenger",
                        "email": "second.passenger@test.com",
                        "passenger_passport_num": "P87654321",
                        "seat_num": "12B",
                        "seat_class": "economy"
                    }
                ]
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "Bad Request"
        assert "passengers" in data["errors"]


class TestListBookingsEndpoint:
    """Test GET /api/bookings/ endpoint."""

    def test_list_bookings_requires_auth(self, client):
        """Booking list requires a bearer token."""
        response = client.get("/api/bookings/")

        assert response.status_code == 401

    def test_list_bookings_user_returns_only_own_bookings(
        self, client, app, auth_headers, test_user
    ):
        """Regular token users should only receive their own bookings."""
        with app.app_context():
            flight1 = _create_test_flight(code="RT103")
            flight2 = _create_test_flight(code="RT104")
            db.session.add(flight1)
            db.session.add(flight2)
            db.session.commit()

            other_user = User(
                firstname="Other",
                lastname="User",
                email="other.user@test.com",
            )
            db.session.add(other_user)
            db.session.commit()
            db.session.refresh(other_user)

            BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight1.id,
                passengers=[
                    {
                        "passenger_name": "Owner",
                        "passenger_passport_num": "P33333333",
                        "seat_num": "3A",
                        "seat_class": "economy"
                    }
                ]
            )
            BookingService.book_tickets(
                user_id=other_user.id,
                flight_id=flight2.id,
                passengers=[
                    {
                        "passenger_name": "Other User",
                        "passenger_passport_num": "P44444444",
                        "seat_num": "4A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.get("/api/bookings/", headers=auth_headers)
            assert response.status_code == 200
            data = response.get_json()

            assert "bookings" in data
            assert "pagination" in data
            returned_user_ids = {item["user_id"] for item in data["bookings"]}
            assert returned_user_ids == {str(test_user.id)}
            assert data["pagination"]["total_items"] == 1

            db.session.delete(other_user)
            db.session.delete(flight1)
            db.session.delete(flight2)
            db.session.commit()

    def test_list_bookings_user_all_true_still_returns_only_own_bookings(
        self, client, app, auth_headers, test_user
    ):
        """The all=true query flag must not widen access for regular users."""
        with app.app_context():
            flight1 = _create_test_flight(code="RT105")
            flight2 = _create_test_flight(code="RT106")
            db.session.add(flight1)
            db.session.add(flight2)
            db.session.commit()

            other_user = User(
                firstname="Other",
                lastname="User",
                email="other.user.all@test.com",
            )
            db.session.add(other_user)
            db.session.commit()
            db.session.refresh(other_user)

            BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight1.id,
                passengers=[
                    {
                        "passenger_name": "Owner",
                        "passenger_passport_num": "P55555555",
                        "seat_num": "5A",
                        "seat_class": "economy"
                    }
                ]
            )
            BookingService.book_tickets(
                user_id=other_user.id,
                flight_id=flight2.id,
                passengers=[
                    {
                        "passenger_name": "Other User",
                        "passenger_passport_num": "P66666666",
                        "seat_num": "6A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.get("/api/bookings/?all=true", headers=auth_headers)
            assert response.status_code == 200
            data = response.get_json()

            returned_user_ids = {item["user_id"] for item in data["bookings"]}
            assert returned_user_ids == {str(test_user.id)}
            assert data["pagination"]["total_items"] == 1

            db.session.delete(other_user)
            db.session.delete(flight1)
            db.session.delete(flight2)
            db.session.commit()

    def test_list_bookings_admin_headers_still_scoped_to_token_user(self, client, app, admin_headers, admin_user, test_user):
        """Bookings list is scoped by bearer token user even if x-api-key exists."""
        with app.app_context():
            flight1 = _create_test_flight(code="RT107")
            flight2 = _create_test_flight(code="RT108")
            db.session.add(flight1)
            db.session.add(flight2)
            db.session.commit()

            other_user = User(
                firstname="Other",
                lastname="User",
                email="other.user.admin@test.com",
            )
            db.session.add(other_user)
            db.session.commit()
            db.session.refresh(other_user)

            BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight1.id,
                passengers=[
                    {
                        "passenger_name": "Admin Visible One",
                        "passenger_passport_num": "P77777777",
                        "seat_num": "7A",
                        "seat_class": "economy"
                    }
                ]
            )
            BookingService.book_tickets(
                user_id=other_user.id,
                flight_id=flight2.id,
                passengers=[
                    {
                        "passenger_name": "Admin Visible Two",
                        "passenger_passport_num": "P88888888",
                        "seat_num": "8A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.get(
                "/api/bookings/?page=1&per_page=10",
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.get_json()
            returned_user_ids = {item["user_id"] for item in data["bookings"]}
            assert returned_user_ids == set()
            assert data["pagination"]["total_items"] == 0

            db.session.delete(other_user)
            db.session.delete(flight1)
            db.session.delete(flight2)
            db.session.commit()

    def test_list_bookings_invalid_pagination(self, client, auth_headers):
        """Invalid page/per_page should return marshmallow error."""
        response = client.get("/api/bookings/?page=0&per_page=0", headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "Bad Request"
        assert "errors" in data


class TestGetBookingEndpoint:
    """Test GET /api/bookings/<booking_id> endpoint."""

    def test_get_booking_success_for_owner(self, client, app, test_user, auth_headers):
        """Owner should retrieve own booking."""
        with app.app_context():
            flight = _create_test_flight(code="RT106")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Owner",
                        "passenger_passport_num": "P66666666",
                        "seat_num": "6A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.get(f"/api/bookings/{booking.id}", headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()
            assert "booking" in data
            assert data["booking"]["id"] == str(booking.id)

            db.session.delete(flight)
            db.session.commit()

    def test_get_booking_forbidden_for_other_user(self, client, app, auth_headers):
        """Regular token users cannot retrieve another user's booking."""
        with app.app_context():
            flight = _create_test_flight(code="RT107")
            db.session.add(flight)
            db.session.commit()

            owner = User(
                firstname="Booking",
                lastname="Owner",
                email="booking.owner@test.com",
            )
            db.session.add(owner)
            db.session.commit()
            db.session.refresh(owner)

            booking, _ = BookingService.book_tickets(
                user_id=owner.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Owner",
                        "passenger_passport_num": "P77777777",
                        "seat_num": "7A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.get(f"/api/bookings/{booking.id}", headers=auth_headers)

            assert response.status_code == 403
            data = response.get_json()
            assert data["error"] == "Forbidden"

            db.session.delete(owner)
            db.session.delete(flight)
            db.session.commit()

    def test_get_booking_not_found(self, client, auth_headers):
        """Unknown booking id should return 404."""
        booking_id = "00000000-0000-0000-0000-000000000001"
        response = client.get(f"/api/bookings/{booking_id}", headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Not Found"


class TestSeatAvailabilityEndpoint:
    """Test GET /api/bookings/availability endpoint."""

    def test_seat_availability_true_then_false(self, client, app, auth_headers):
        """Availability should flip after ticket purchase."""
        with app.app_context():
            flight = _create_test_flight(code="RT108")
            db.session.add(flight)
            db.session.commit()

            available_response = client.get(
                f"/api/bookings/availability?flight_id={flight.id}&seat_num=9A",
                headers=auth_headers
            )
            assert available_response.status_code == 200
            assert available_response.get_json()["available"] is True

            create_response = client.post(
                "/api/bookings/",
                headers=auth_headers,
                json={
                    "flight_id": str(flight.id),
                    "passengers": [
                        {
                            "passenger_name": "Seat Owner",
                            "email": "seat.owner@test.com",
                            "passenger_passport_num": "P88888888",
                            "seat_num": "9A",
                            "seat_class": "economy"
                        }
                    ]
                }
            )
            assert create_response.status_code == 201

            unavailable_response = client.get(
                f"/api/bookings/availability?flight_id={flight.id}&seat_num=9A",
                headers=auth_headers
            )
            assert unavailable_response.status_code == 200
            assert unavailable_response.get_json()["available"] is False

            db.session.delete(flight)
            db.session.commit()

    def test_seat_availability_validation_error(self, client, auth_headers):
        """Invalid seat length should fail schema validation."""
        seat_num = quote("ABCDE")
        response = client.get(
            f"/api/bookings/availability?flight_id=fe4a1338-4b98-4b51-9f5c-1234567890ab&seat_num={seat_num}",
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "Bad Request"
        assert "errors" in data

    def test_seat_availability_without_auth_success(self, client, app):
        """Availability endpoint is public."""
        with app.app_context():
            flight = _create_test_flight(code="RT109")
            db.session.add(flight)
            db.session.commit()

            response = client.get(f"/api/bookings/availability?flight_id={flight.id}&seat_num=1A")
            assert response.status_code == 200
            assert response.get_json()["available"] is True

            db.session.delete(flight)
            db.session.commit()


class TestUpdateBookingEndpoint:
    """Test PUT /api/bookings/<booking_id> endpoint."""

    def test_update_booking_success_by_owner(self, client, app, test_user, auth_headers):
        """Owner can successfully update their booking status."""
        with app.app_context():
            flight = _create_test_flight(code="RT110")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test Passenger",
                        "passenger_passport_num": "P99999999",
                        "seat_num": "10A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.put(
                f"/api/bookings/{booking.id}",
                headers=auth_headers,
                json={"booking_status": "paid"}
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["message"] == "Booking updated successfully"
            assert data["booking"]["booking_status"] == "paid"
            assert data["booking"]["id"] == str(booking.id)

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_booked_to_cancelled(self, client, app, test_user, auth_headers):
        """Update booking from booked to cancelled."""
        with app.app_context():
            flight = _create_test_flight(code="RT111")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test Passenger",
                        "passenger_passport_num": "P10101010",
                        "seat_num": "11A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.put(
                f"/api/bookings/{booking.id}",
                headers=auth_headers,
                json={"booking_status": "cancelled"}
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["booking"]["booking_status"] == "cancelled"

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_paid_to_refunded(self, client, app, test_user, auth_headers):
        """Update booking from paid to refunded."""
        with app.app_context():
            flight = _create_test_flight(code="RT112")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test Passenger",
                        "passenger_passport_num": "P11111112",
                        "seat_num": "12A",
                        "seat_class": "economy"
                    }
                ],
                booking_status="paid"
            )

            response = client.put(
                f"/api/bookings/{booking.id}",
                headers=auth_headers,
                json={"booking_status": "refunded"}
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["booking"]["booking_status"] == "refunded"

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_cannot_update_cancelled(self, client, app, test_user, auth_headers):
        """Cannot update a booking that is already cancelled."""
        with app.app_context():
            flight = _create_test_flight(code="RT113")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test Passenger",
                        "passenger_passport_num": "P12121212",
                        "seat_num": "13A",
                        "seat_class": "economy"
                    }
                ],
                booking_status="cancelled"
            )

            response = client.put(
                f"/api/bookings/{booking.id}",
                headers=auth_headers,
                json={"booking_status": "paid"}
            )

            assert response.status_code == 409
            data = response.get_json()
            assert data["error"] == "Conflict"
            assert "cancelled" in data["message"].lower()

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_cannot_update_refunded(self, client, app, test_user, auth_headers):
        """Cannot update a booking that is already refunded."""
        with app.app_context():
            flight = _create_test_flight(code="RT114")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test Passenger",
                        "passenger_passport_num": "P13131313",
                        "seat_num": "14A",
                        "seat_class": "economy"
                    }
                ],
                booking_status="refunded"
            )

            response = client.put(
                f"/api/bookings/{booking.id}",
                headers=auth_headers,
                json={"booking_status": "paid"}
            )

            assert response.status_code == 409
            data = response.get_json()
            assert data["error"] == "Conflict"
            assert "refunded" in data["message"].lower()

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_invalid_status(self, client, app, test_user, auth_headers):
        """Invalid booking_status should fail validation."""
        with app.app_context():
            flight = _create_test_flight(code="RT115")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test Passenger",
                        "passenger_passport_num": "P14141414",
                        "seat_num": "15A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.put(
                f"/api/bookings/{booking.id}",
                headers=auth_headers,
                json={"booking_status": "invalid_status"}
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "Bad Request"
            assert "errors" in data

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_missing_status(self, client, app, test_user, auth_headers):
        """booking_status is required in request body."""
        with app.app_context():
            flight = _create_test_flight(code="RT116")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test Passenger",
                        "passenger_passport_num": "P15151515",
                        "seat_num": "16A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.put(
                f"/api/bookings/{booking.id}",
                headers=auth_headers,
                json={}
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "Bad Request"
            assert "errors" in data

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_not_found(self, client, auth_headers):
        """Update non-existent booking returns 404."""
        booking_id = "00000000-0000-0000-0000-000000000002"
        response = client.put(
            f"/api/bookings/{booking_id}",
            headers=auth_headers,
            json={"booking_status": "paid"}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Not Found"

    def test_update_booking_forbidden_for_other_user(self, client, app, auth_headers):
        """Regular token users cannot update another user's booking."""
        with app.app_context():
            flight = _create_test_flight(code="RT117")
            db.session.add(flight)
            db.session.commit()

            owner = User(
                firstname="Booking",
                lastname="Owner",
                email="owner.update@test.com",
            )
            db.session.add(owner)
            db.session.commit()
            db.session.refresh(owner)

            booking, _ = BookingService.book_tickets(
                user_id=owner.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Owner Passenger",
                        "passenger_passport_num": "P16161616",
                        "seat_num": "17A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.put(
                f"/api/bookings/{booking.id}",
                headers=auth_headers,
                json={"booking_status": "paid"}
            )

            assert response.status_code == 403
            data = response.get_json()
            assert data["error"] == "Forbidden"

            db.session.delete(owner)
            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_admin_headers_cannot_update_other_users(self, client, app, test_user, admin_headers):
        """x-api-key does not override booking ownership checks."""
        with app.app_context():
            flight = _create_test_flight(code="RT118")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "User Passenger",
                        "passenger_passport_num": "P17171717",
                        "seat_num": "18A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.put(
                f"/api/bookings/{booking.id}",
                headers=admin_headers,
                json={"booking_status": "paid"}
            )

            assert response.status_code == 403
            data = response.get_json()
            assert data["error"] == "Forbidden"

            db.session.delete(flight)
            db.session.commit()

    def test_update_booking_requires_auth(self, client):
        """Updating a booking requires a bearer token."""
        response = client.put(
            "/api/bookings/00000000-0000-0000-0000-000000000002",
            json={"booking_status": "paid"}
        )

        assert response.status_code == 401


class TestCancelBookingEndpoint:
    """Test DELETE /api/bookings/<booking_id> endpoint."""

    def test_cancel_booking_success_by_owner(self, client, app, test_user, auth_headers):
        """Owner can successfully cancel their booking."""
        with app.app_context():
            flight = _create_test_flight(code="RT120")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test Passenger",
                        "passenger_passport_num": "P19191919",
                        "seat_num": "20A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.delete(
                f"/api/bookings/{booking.id}",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["message"] == "Booking cancelled successfully"
            assert data["booking"]["booking_status"] == "cancelled"
            assert data["booking"]["id"] == str(booking.id)

            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_paid_status(self, client, app, test_user, auth_headers):
        """Can cancel a paid booking."""
        with app.app_context():
            flight = _create_test_flight(code="RT121")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test Passenger",
                        "passenger_passport_num": "P20202020",
                        "seat_num": "21A",
                        "seat_class": "economy"
                    }
                ],
                booking_status="paid"
            )

            response = client.delete(
                f"/api/bookings/{booking.id}",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["booking"]["booking_status"] == "cancelled"

            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_already_cancelled(self, client, app, test_user, auth_headers):
        """Cannot cancel an already cancelled booking."""
        with app.app_context():
            flight = _create_test_flight(code="RT122")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test Passenger",
                        "passenger_passport_num": "P21212121",
                        "seat_num": "22A",
                        "seat_class": "economy"
                    }
                ],
                booking_status="cancelled"
            )

            response = client.delete(
                f"/api/bookings/{booking.id}",
                headers=auth_headers
            )

            assert response.status_code == 409
            data = response.get_json()
            assert data["error"] == "Conflict"
            assert "already cancelled" in data["message"].lower()

            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_cannot_cancel_refunded(self, client, app, test_user, auth_headers):
        """Cannot cancel a refunded booking."""
        with app.app_context():
            flight = _create_test_flight(code="RT123")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test Passenger",
                        "passenger_passport_num": "P22222222",
                        "seat_num": "23A",
                        "seat_class": "economy"
                    }
                ],
                booking_status="refunded"
            )

            response = client.delete(
                f"/api/bookings/{booking.id}",
                headers=auth_headers
            )

            assert response.status_code == 409
            data = response.get_json()
            assert data["error"] == "Conflict"
            assert "refunded" in data["message"].lower()

            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_not_found(self, client, auth_headers):
        """Cancel non-existent booking returns 404."""
        booking_id = "00000000-0000-0000-0000-000000000003"
        response = client.delete(
            f"/api/bookings/{booking_id}",
            headers=auth_headers
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Not Found"

    def test_cancel_booking_forbidden_for_other_user(self, client, app, auth_headers):
        """Regular token users cannot cancel another user's booking."""
        with app.app_context():
            flight = _create_test_flight(code="RT124")
            db.session.add(flight)
            db.session.commit()

            owner = User(
                firstname="Booking",
                lastname="Owner",
                email="owner.cancel@test.com",
            )
            db.session.add(owner)
            db.session.commit()
            db.session.refresh(owner)

            booking, _ = BookingService.book_tickets(
                user_id=owner.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Owner Passenger",
                        "passenger_passport_num": "P23232323",
                        "seat_num": "24A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.delete(f"/api/bookings/{booking.id}", headers=auth_headers)

            assert response.status_code == 403
            data = response.get_json()
            assert data["error"] == "Forbidden"

            db.session.delete(owner)
            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_admin_can_cancel_any_user(self, client, app, test_user, admin_headers):
        """Admin x-api-key (with or without Bearer) can cancel another user's booking."""
        with app.app_context():
            flight = _create_test_flight(code="RT125")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "User Passenger",
                        "passenger_passport_num": "P24242424",
                        "seat_num": "25A",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.delete(
                f"/api/bookings/{booking.id}",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["booking"]["booking_status"] == "cancelled"

            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_admin_api_key_only(self, client, app, test_user):
        """DELETE with only x-api-key cancels any booking (auxiliary sweep use case)."""
        with app.app_context():
            flight = _create_test_flight(code="RT125B")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "User Passenger",
                        "passenger_passport_num": "P25252525",
                        "seat_num": "25B",
                        "seat_class": "economy"
                    }
                ]
            )

            response = client.delete(
                f"/api/bookings/{booking.id}",
                headers={"x-api-key": os.environ["ADMIN_API_KEY"]},
            )

            assert response.status_code == 200
            assert response.get_json()["booking"]["booking_status"] == "cancelled"

            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_invalid_admin_key(self, client, app, test_user, auth_headers):
        """Wrong x-api-key returns 403 even if Bearer is a valid owner token."""
        with app.app_context():
            flight = _create_test_flight(code="RT125C")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "User Passenger",
                        "passenger_passport_num": "P26262626",
                        "seat_num": "25C",
                        "seat_class": "economy"
                    }
                ]
            )

            headers = {**auth_headers, "x-api-key": "not-the-admin-key"}
            response = client.delete(f"/api/bookings/{booking.id}", headers=headers)

            assert response.status_code == 403
            assert response.get_json()["error"] == "Forbidden"

            db.session.delete(flight)
            db.session.commit()

    def test_cancel_booking_requires_auth(self, client):
        """Cancelling a booking requires admin x-api-key or owner bearer token."""
        response = client.delete("/api/bookings/00000000-0000-0000-0000-000000000003")

        assert response.status_code == 401

    def test_cancel_booking_updates_timestamp(self, client, app, test_user, auth_headers):
        """Cancelling a booking updates the updated_at timestamp."""
        with app.app_context():
            flight = _create_test_flight(code="RT127")
            db.session.add(flight)
            db.session.commit()

            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=[
                    {
                        "passenger_name": "Test Passenger",
                        "passenger_passport_num": "P26262626",
                        "seat_num": "27A",
                        "seat_class": "economy"
                    }
                ]
            )

            original_updated_at = booking.updated_at

            import time
            time.sleep(0.1)

            response = client.delete(
                f"/api/bookings/{booking.id}",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.get_json()

            # Parse timestamps and compare
            from datetime import datetime
            response_updated_at = datetime.fromisoformat(data["booking"]["updated_at"])
            assert response_updated_at > original_updated_at

            db.session.delete(flight)
            db.session.commit()


class TestBookingErrorHandling:
    """Test error handling and exception paths in booking endpoints."""

    def test_create_booking_with_invalid_json_format(self, client, auth_headers):
        """Test create booking with invalid JSON format."""
        response = client.post(
            "/api/bookings/",
            headers=auth_headers,
            data="invalid json",
            content_type="application/json"
        )
        # Invalid JSON returns 500 from Flask request parsing
        assert response.status_code in [400, 500]

    def test_create_booking_empty_passengers_list(self, client, auth_headers):
        """Test create booking with empty passengers list."""
        response = client.post(
            "/api/bookings/",
            headers=auth_headers,
            json={
                "flight_id": "fe4a1338-4b98-4b51-9f5c-1234567890ab",
                "passengers": []
            }
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "Bad Request"

    def test_seat_availability_invalid_flight_id(self, client, auth_headers):
        """Test seat availability with invalid flight ID."""
        response = client.get(
            "/api/bookings/availability?flight_id=invalid&seat_num=1A",
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_seat_availability_missing_seat_num(self, client, auth_headers):
        """Test seat availability with missing seat number."""
        response = client.get(
            f"/api/bookings/availability?flight_id=fe4a1338-4b98-4b51-9f5c-1234567890ab",
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_seat_availability_missing_flight_id(self, client, auth_headers):
        """Test seat availability with missing flight ID."""
        response = client.get(
            "/api/bookings/availability?seat_num=1A",
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_list_bookings_with_pagination(self, client, app, auth_headers, test_user):
        """Test list bookings with pagination."""
        with app.app_context():
            flight = _create_test_flight()
            db.session.add(flight)
            db.session.commit()

            for i in range(5):
                BookingService.book_tickets(
                    user_id=test_user.id,
                    flight_id=flight.id,
                    passengers=[
                        {
                            "passenger_name": f"User{i}",
                            "passenger_passport_num": f"P{i:08d}",
                            "seat_num": f"{i+1}A",
                            "seat_class": "economy"
                        }
                    ]
                )

        response = client.get(
            "/api/bookings/?page=1&per_page=2",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 2

    def test_list_bookings_invalid_page(self, client, auth_headers):
        """Test list bookings with invalid page number."""
        response = client.get(
            "/api/bookings/?page=invalid&per_page=10",
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_seat_availability_ValueError_exception(self, client, app, auth_headers):
        """Test seat availability endpoint handles ValueError from service."""
        with app.app_context():
            flight = _create_test_flight()
            db.session.add(flight)
            db.session.commit()
            flight_id = flight.id

            # Monkey patch the service method to raise ValueError
            original_method = BookingService.get_seat_availability
            def raise_value_error(*args, **kwargs):
                raise ValueError("Invalid seat format")
            BookingService.get_seat_availability = raise_value_error

        response = client.get(
            f"/api/bookings/availability?flight_id={flight_id}&seat_num=1A",
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "Bad Request"
        assert "invalid seat" in data["message"].lower()

        # Restore original method
        with app.app_context():
            BookingService.get_seat_availability = original_method

    def test_seat_availability_unexpected_exception(self, client, app, auth_headers):
        """Test seat availability endpoint handles unexpected exceptions."""
        with app.app_context():
            flight = _create_test_flight()
            db.session.add(flight)
            db.session.commit()
            flight_id = flight.id

            # Monkey patch the service method to raise an exception
            original_method = BookingService.get_seat_availability
            def raise_exception(*args, **kwargs):
                raise Exception("Unexpected error in service")
            BookingService.get_seat_availability = raise_exception

        response = client.get(
            f"/api/bookings/availability?flight_id={flight_id}&seat_num=1A",
            headers=auth_headers
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data["error"] == "Internal Server Error"
        assert "unexpected" in data["message"].lower()

        # Restore original method
        with app.app_context():
            BookingService.get_seat_availability = original_method


class TestBookingRoutesExceptionHandlers:
    """Test broad exception handlers in booking routes."""

    def test_create_booking_unexpected_exception(self, client, app, auth_headers, sample_flights):
        """Test create_booking handles unexpected exceptions."""
        with app.app_context():
            with patch('ticket_management_system.resources.bookings.BookingService.book_tickets') as mock_service:
                mock_service.side_effect = Exception('Database error during booking creation')

                response = client.post(
                    '/api/bookings/',
                    json={
                        'flight_id': str(sample_flights[0].id),
                        'passengers': [
                            {
                                'passenger_name': 'John Doe',
                                'email': 'exception.owner@test.com',
                                'passenger_passport_num': 'P12345678',
                                'seat_num': '12A',
                                'seat_class': 'economy'
                            }
                        ]
                    },
                    headers=auth_headers
                )

                assert response.status_code == 500
                data = response.get_json()
                assert 'error' in data
                assert 'Internal Server Error' in data['error']
                assert 'message' in data

    def test_list_bookings_unexpected_exception(self, client, app, auth_headers):
        """Test list_bookings handles unexpected exceptions."""
        with app.app_context():
            with patch('ticket_management_system.resources.bookings.BookingService.get_paginated_bookings') as mock_service:
                mock_service.side_effect = Exception('Database connection failed')

                response = client.get(
                    '/api/bookings/?page=1&per_page=10',
                    headers=auth_headers
                )

                assert response.status_code == 500
                data = response.get_json()
                assert 'error' in data
                assert 'Internal Server Error' in data['error']

    def test_update_booking_unexpected_exception(self, client, app, auth_headers, test_user, sample_flights):
        """Test update_booking handles unexpected exceptions."""
        booking_id = None
        with app.app_context():
            from ticket_management_system.models import BookingStatus
            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=sample_flights[0].id,
                passengers=[{
                    "passenger_name": "Test",
                    "passenger_passport_num": "P12345",
                    "seat_num": "1A",
                    "seat_class": "economy"
                }],
                booking_status=BookingStatus.booked
            )
            booking_id = booking.id

        with patch('ticket_management_system.resources.bookings.BookingService.update_booking') as mock_service:
            mock_service.side_effect = Exception('Database update failed')

            response = client.put(
                f'/api/bookings/{booking_id}',
                json={'booking_status': 'paid'},
                headers=auth_headers
            )

            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
            assert 'Internal Server Error' in data['error']

    def test_cancel_booking_unexpected_exception(self, client, app, auth_headers, test_user, sample_flights):
        """Test cancel_booking handles unexpected exceptions."""
        booking_id = None
        with app.app_context():
            from ticket_management_system.models import BookingStatus
            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=sample_flights[0].id,
                passengers=[{
                    "passenger_name": "Test",
                    "passenger_passport_num": "P12345",
                    "seat_num": "2A",
                    "seat_class": "economy"
                }],
                booking_status=BookingStatus.booked
            )
            booking_id = booking.id

        with patch('ticket_management_system.resources.bookings.BookingService.cancel_booking') as mock_service:
            mock_service.side_effect = Exception('Database delete failed')

            response = client.delete(
                f'/api/bookings/{booking_id}',
                headers=auth_headers
            )

            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
            assert 'Internal Server Error' in data['error']

    def test_get_booking_unexpected_exception(self, client, app, auth_headers, test_user, sample_flights):
        """Test get_booking handles unexpected exceptions."""
        booking_id = None
        with app.app_context():
            from ticket_management_system.models import BookingStatus
            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=sample_flights[0].id,
                passengers=[{
                    "passenger_name": "Test",
                    "passenger_passport_num": "P12345",
                    "seat_num": "3A",
                    "seat_class": "economy"
                }],
                booking_status=BookingStatus.booked
            )
            booking_id = booking.id

        with patch('ticket_management_system.resources.bookings.BookingService.get_booking_by_id') as mock_service:
            mock_service.side_effect = Exception('Database query failed')

            response = client.get(
                f'/api/bookings/{booking_id}',
                headers=auth_headers
            )

            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
            assert 'Internal Server Error' in data['error']

    def test_get_seat_availability_unexpected_exception(self, client, app, auth_headers, sample_flights):
        """Test get_seat_availability handles unexpected exceptions."""
        flight_id = None
        with app.app_context():
            flight_id = sample_flights[0].id

        with patch('ticket_management_system.resources.bookings.BookingService.get_seat_availability') as mock_service:
            mock_service.side_effect = Exception('Database query error')

            response = client.get(
                f'/api/bookings/availability?flight_id={flight_id}&seat_num=12A',
                headers=auth_headers
            )

            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
            assert 'Internal Server Error' in data['error']


