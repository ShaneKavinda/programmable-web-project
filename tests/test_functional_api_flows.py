"""Functional tests covering end-to-end API workflows."""

from datetime import datetime, timedelta
import uuid

import pytest


pytestmark = pytest.mark.integration


def _auth_headers(token):
    """Build bearer auth headers."""
    return {"Authorization": f"Bearer {token}"}


def _issue_token_for_user(client, user):
    """Request a scoped token for an existing user ID."""
    response = client.get(f"/api/users/{user.id}/token")

    assert response.status_code == 200
    return response.get_json()


def _build_flight_payload(
    *,
    origin_airport="HEL",
    destination_airport="LHR",
    base_price="400.00",
):
    """Create a valid flight payload with future timestamps."""
    departure_time = datetime.now() + timedelta(days=30)
    arrival_time = departure_time + timedelta(hours=3, minutes=20)

    return {
        "flight_code": f"F{uuid.uuid4().hex[:7].upper()}",
        "origin_airport": origin_airport,
        "destination_airport": destination_airport,
        "departure_time": departure_time.strftime("%Y-%m-%d %H:%M:%S"),
        "arrival_time": arrival_time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_price": base_price,
    }


def test_user_can_get_scoped_token_update_profile_and_receive_refreshed_token(client, test_user):
    """A user ID should grant a scoped token that refreshes after activity."""
    token_data = _issue_token_for_user(client, test_user)
    user_headers = _auth_headers(token_data["token"])

    me_response = client.get("/api/users/me", headers=user_headers)
    assert me_response.status_code == 200
    assert "X-Refreshed-Token" in me_response.headers
    me_data = me_response.get_json()
    assert me_data["user"]["email"] == test_user.email

    updated_email = f"updated_{uuid.uuid4().hex[:8]}@example.com"
    update_response = client.patch(
        "/api/users/me",
        headers=_auth_headers(me_response.headers["X-Refreshed-Token"]),
        json={
            "firstname": "Updated",
            "lastname": "Traveller",
            "email": updated_email,
        },
    )

    assert update_response.status_code == 200
    assert "X-Refreshed-Token" in update_response.headers
    update_data = update_response.get_json()
    assert update_data["user"]["firstname"] == "Updated"
    assert update_data["user"]["lastname"] == "Traveller"
    assert update_data["user"]["email"] == updated_email

    updated_me_response = client.get("/api/users/me", headers=_auth_headers(update_response.headers["X-Refreshed-Token"]))
    assert updated_me_response.status_code == 200
    updated_me_data = updated_me_response.get_json()
    assert updated_me_data["user"]["email"] == updated_email

    login_response = client.post("/api/users/login", json={"email": updated_email, "password": "anything"})
    register_response = client.post("/api/users/register", json={})
    assert login_response.status_code == 404
    assert register_response.status_code == 404


def test_admin_can_create_update_and_delete_flights_visible_to_users(client, admin_headers, test_user):
    """Flight CRUD changes should be reflected across authenticated API endpoints."""
    user_registration = _issue_token_for_user(client, test_user)
    user_headers = _auth_headers(user_registration["token"])

    create_response = client.post(
        "/api/flights/",
        headers=admin_headers,
        json=_build_flight_payload(origin_airport="HEL", destination_airport="LHR", base_price="450.00"),
    )

    assert create_response.status_code == 201
    created_flight = create_response.get_json()["flight"]
    flight_id = created_flight["id"]

    search_created_response = client.get(
        "/api/flights/search?origin_airport=HEL&destination_airport=LHR",
        headers=user_headers,
    )
    assert search_created_response.status_code == 200
    created_search_data = search_created_response.get_json()
    assert any(flight["id"] == flight_id for flight in created_search_data["flights"])

    update_response = client.put(
        f"/api/flights/{flight_id}",
        headers=admin_headers,
        json={
            "destination_airport": "AMS",
            "base_price": "525.00",
        },
    )

    assert update_response.status_code == 200
    updated_flight = update_response.get_json()["flight"]
    assert updated_flight["destination_airport"] == "AMS"
    assert updated_flight["base_price"] == "525.00"

    stale_search_response = client.get(
        "/api/flights/search?origin_airport=HEL&destination_airport=LHR",
        headers=user_headers,
    )
    assert stale_search_response.status_code == 200
    stale_search_data = stale_search_response.get_json()
    assert all(flight["id"] != flight_id for flight in stale_search_data["flights"])

    updated_search_response = client.get(
        "/api/flights/search?origin_airport=HEL&destination_airport=AMS",
        headers=user_headers,
    )
    assert updated_search_response.status_code == 200
    updated_search_data = updated_search_response.get_json()
    assert any(flight["id"] == flight_id for flight in updated_search_data["flights"])

    delete_response = client.delete(f"/api/flights/{flight_id}", headers=admin_headers)
    assert delete_response.status_code == 200

    deleted_search_response = client.get(
        "/api/flights/search?origin_airport=HEL&destination_airport=AMS",
        headers=user_headers,
    )
    assert deleted_search_response.status_code == 200
    deleted_search_data = deleted_search_response.get_json()
    assert all(flight["id"] != flight_id for flight in deleted_search_data["flights"])


def test_user_can_book_pay_and_observe_booking_state_changes(client, admin_headers, test_user):
    """Booking, availability, payment, and retrieval endpoints should stay in sync."""
    user_registration = _issue_token_for_user(client, test_user)
    user_headers = _auth_headers(user_registration["token"])

    create_flight_response = client.post(
        "/api/flights/",
        headers=admin_headers,
        json=_build_flight_payload(origin_airport="JFK", destination_airport="SFO", base_price="400.00"),
    )
    assert create_flight_response.status_code == 201
    flight_id = create_flight_response.get_json()["flight"]["id"]

    available_response = client.get(
        f"/api/bookings/availability?flight_id={flight_id}&seat_num=4A",
        headers=user_headers,
    )
    assert available_response.status_code == 200
    assert available_response.get_json()["available"] is True

    booking_response = client.post(
        "/api/bookings/",
        headers=user_headers,
        json={
            "user_id": user_registration["user"]["id"],
            "flight_id": flight_id,
            "passengers": [
                {
                    "passenger_name": "Alex Flyer",
                    "email": test_user.email,
                    "passenger_passport_num": "PX123456",
                    "seat_num": "4A",
                    "seat_class": "economy",
                },
                {
                    "passenger_name": "Jamie Flyer",
                    "passenger_passport_num": "PX654321",
                    "seat_num": "4B",
                    "seat_class": "business",
                },
            ],
        },
    )

    assert booking_response.status_code == 201
    booking_data = booking_response.get_json()["booking"]
    booking_id = booking_data["id"]
    assert booking_data["flight_id"] == flight_id
    assert booking_data["booking_status"] == "booked"
    assert booking_data["total_price"] == "1400.00"
    assert {ticket["seat_num"] for ticket in booking_data["tickets"]} == {"4A", "4B"}

    booked_availability_response = client.get(
        f"/api/bookings/availability?flight_id={flight_id}&seat_num=4A",
        headers=user_headers,
    )
    assert booked_availability_response.status_code == 200
    assert booked_availability_response.get_json()["available"] is False

    list_response = client.get("/api/bookings/", headers=user_headers)
    assert list_response.status_code == 200
    list_data = list_response.get_json()
    assert any(booking["id"] == booking_id for booking in list_data["bookings"])

    payment_response = client.post(
        "/api/payments/",
        headers=user_headers,
        json={
            "booking_number": booking_id,
            "credit_card_number": "1234567890123456",
            "security_code": "123",
        },
    )

    assert payment_response.status_code == 200
    payment_data = payment_response.get_json()
    assert payment_data["status"] == "paid"

    booking_detail_response = client.get(f"/api/bookings/{booking_id}", headers=user_headers)
    assert booking_detail_response.status_code == 200
    booking_detail = booking_detail_response.get_json()["booking"]
    assert booking_detail["booking_status"] == "paid"
    assert booking_detail["total_price"] == "1400.00"
    assert len(booking_detail["tickets"]) == 2
