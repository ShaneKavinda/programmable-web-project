"""Comprehensive unit tests for payment processing - covers all code paths."""
import uuid
from decimal import Decimal
from datetime import datetime
from ticket_management_system.extensions import db
from ticket_management_system.models import (
    Flight, FlightStatus, Booking, BookingStatus, User
)
from ticket_management_system.resources.booking_service import BookingService
from ticket_management_system.resources.user_service import UserService


class TestPaymentValidation:
    """Test payment input validation."""

    def test_missing_booking_number(self, client, auth_headers):
        """Test missing booking number."""
        response = client.post(
            '/api/payments/',
            json={'credit_card_number': '1234567890123456', 'security_code': '123'},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert 'required' in response.get_json()['message'].lower()

    def test_missing_credit_card(self, client, auth_headers):
        """Test missing credit card."""
        response = client.post(
            '/api/payments/',
            json={'booking_number': str(uuid.uuid4()), 'security_code': '123'},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert 'required' in response.get_json()['message'].lower()

    def test_missing_security_code(self, client, auth_headers):
        """Test missing security code."""
        response = client.post(
            '/api/payments/',
            json={'booking_number': str(uuid.uuid4()), 'credit_card_number': '1234567890123456'},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert 'required' in response.get_json()['message'].lower()

    def test_card_too_short(self, client, auth_headers):
        """Test credit card too short."""
        response = client.post(
            '/api/payments/',
            json={'booking_number': str(uuid.uuid4()), 'credit_card_number': '12345', 'security_code': '123'},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert '16 digits' in response.get_json()['message']

    def test_card_too_long(self, client, auth_headers):
        """Test credit card too long."""
        response = client.post(
            '/api/payments/',
            json={'booking_number': str(uuid.uuid4()), 'credit_card_number': '123456789012345678', 'security_code': '123'},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert '16 digits' in response.get_json()['message']

    def test_card_non_numeric(self, client, auth_headers):
        """Test non-numeric credit card."""
        response = client.post(
            '/api/payments/',
            json={'booking_number': str(uuid.uuid4()), 'credit_card_number': 'abcdefghijklmnop', 'security_code': '123'},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert '16 digits' in response.get_json()['message']

    def test_code_too_short(self, client, auth_headers):
        """Test security code too short."""
        response = client.post(
            '/api/payments/',
            json={'booking_number': str(uuid.uuid4()), 'credit_card_number': '1234567890123456', 'security_code': '12'},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert '3 digits' in response.get_json()['message']

    def test_code_too_long(self, client, auth_headers):
        """Test security code too long."""
        response = client.post(
            '/api/payments/',
            json={'booking_number': str(uuid.uuid4()), 'credit_card_number': '1234567890123456', 'security_code': '1234'},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert '3 digits' in response.get_json()['message']

    def test_code_non_numeric(self, client, auth_headers):
        """Test non-numeric security code."""
        response = client.post(
            '/api/payments/',
            json={'booking_number': str(uuid.uuid4()), 'credit_card_number': '1234567890123456', 'security_code': 'abc'},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert '3 digits' in response.get_json()['message']

    def test_empty_body(self, client, auth_headers):
        """Test empty JSON body."""
        response = client.post('/api/payments/', json={}, headers=auth_headers)
        assert response.status_code == 400

    def test_no_json(self, client, auth_headers):
        """Test no JSON body."""
        response = client.post(
            '/api/payments/',
            data='',
            content_type='application/json',
            headers=auth_headers
        )
        assert response.status_code == 400


class TestPaymentAuthentication:
    """Test authentication requirements."""

    def test_requires_auth(self, client):
        """Test payment requires authentication."""
        response = client.post(
            '/api/payments/',
            json={
                'booking_number': str(uuid.uuid4()),
                'credit_card_number': '1234567890123456',
                'security_code': '123'
            }
        )
        assert response.status_code == 401


class TestPaymentBookingNotFound:
    """Test payment for non-existent bookings."""

    def test_invalid_uuid_format(self, client, auth_headers):
        """Test payment with invalid UUID format."""
        response = client.post(
            '/api/payments/',
            json={
                'booking_number': 'not-a-uuid',
                'credit_card_number': '1234567890123456',
                'security_code': '123'
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        assert 'Invalid booking ID format' in response.get_json()['message']

    def test_booking_not_found(self, client, auth_headers):
        """Test payment for non-existent booking with valid UUID."""
        fake_booking_id = str(uuid.uuid4())
        response = client.post(
            '/api/payments/',
            json={
                'booking_number': fake_booking_id,
                'credit_card_number': '1234567890123456',
                'security_code': '123'
            },
            headers=auth_headers
        )
        assert response.status_code == 404
        assert 'Booking not found' in response.get_json()['message']


class TestPaymentSuccessful:
    """Test successful payment processing."""

    def test_payment_successful(self, client, app, test_user):
        """Test successful payment processing."""
        with app.app_context():
            # Create flight
            flight = Flight(
                flight_code=f'PAY_SUCCESS_{uuid.uuid4().hex[:6]}',
                origin_airport='NYC',
                destination_airport='LAX',
                departure_time=datetime(2026, 8, 15, 10, 0),
                arrival_time=datetime(2026, 8, 15, 14, 0),
                base_price=Decimal('500.00'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            # Create booking
            passengers = [
                {
                    'passenger_name': 'Payment Test',
                    'passenger_passport_num': f'PAY{uuid.uuid4().hex[:6]}',
                    'seat_num': '1A',
                    'seat_class': 'economy'
                }
            ]
            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=passengers
            )
            booking_id = str(booking.id)

        # Get auth token
        with app.app_context():
            token = UserService.generate_token(test_user)
            headers = {'Authorization': f'Bearer {token}'}

        # Process payment
        response = client.post(
            '/api/payments/',
            json={
                'booking_number': booking_id,
                'credit_card_number': '1234567890123456',
                'security_code': '123'
            },
            headers=headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'Payment successful' in data['message']
        assert data['status'] == 'paid'

        # Verify booking status changed in database
        with app.app_context():
            import uuid as uuid_module
            booking_uuid = uuid_module.UUID(booking_id)
            updated_booking = Booking.query.filter_by(id=booking_uuid).first()
            assert updated_booking.booking_status == BookingStatus.paid


class TestPaymentPermissionDenied:
    """Test payment permission checks."""

    def test_payment_forbidden_for_other_user(self, client, app):
        """Test that user cannot pay for another user's booking."""
        user1_id = None
        user2_id = None
        booking_id = None

        with app.app_context():
            # Create two users
            user1 = User(
                firstname='User1',
                lastname='One',
                email=f'user1_{uuid.uuid4().hex[:8]}@test.com',
            )
            user2 = User(
                firstname='User2',
                lastname='Two',
                email=f'user2_{uuid.uuid4().hex[:8]}@test.com',
            )
            db.session.add(user1)
            db.session.add(user2)
            db.session.commit()
            user1_id = user1.id
            user2_id = user2.id

            # Create flight
            flight = Flight(
                flight_code=f'PAY_PERM_{uuid.uuid4().hex[:6]}',
                origin_airport='LAX',
                destination_airport='NYC',
                departure_time=datetime(2026, 9, 1, 10, 0),
                arrival_time=datetime(2026, 9, 1, 14, 0),
                base_price=Decimal('600.00'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            # User1 creates booking
            passengers = [
                {
                    'passenger_name': 'User One',
                    'passenger_passport_num': f'U1_{uuid.uuid4().hex[:6]}',
                    'seat_num': '10A',
                    'seat_class': 'economy'
                }
            ]
            booking, _ = BookingService.book_tickets(
                user_id=user1.id,
                flight_id=flight.id,
                passengers=passengers
            )
            booking_id = str(booking.id)

        # User2 tries to pay for user1's booking
        with app.app_context():
            user2 = db.session.get(User, user2_id)
            user2_token = UserService.generate_token(user2)
            headers = {'Authorization': f'Bearer {user2_token}'}

        response = client.post(
            '/api/payments/',
            json={
                'booking_number': booking_id,
                'credit_card_number': '1234567890123456',
                'security_code': '123'
            },
            headers=headers
        )

        assert response.status_code == 403
        assert 'cannot pay for another' in response.get_json()['message'].lower()


class TestPaymentAlreadyPaid:
    """Test conflict when booking is already paid."""

    def test_payment_rejected_already_paid(self, client, app, test_user):
        """Test that payment is rejected for already paid booking."""
        with app.app_context():
            # Create flight
            flight = Flight(
                flight_code=f'PAY_PAID_{uuid.uuid4().hex[:6]}',
                origin_airport='ORD',
                destination_airport='DEN',
                departure_time=datetime(2026, 9, 5, 10, 0),
                arrival_time=datetime(2026, 9, 5, 14, 0),
                base_price=Decimal('400.00'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            # Create booking
            passengers = [
                {
                    'passenger_name': 'Already Paid',
                    'passenger_passport_num': f'ALP{uuid.uuid4().hex[:6]}',
                    'seat_num': '15A',
                    'seat_class': 'business'
                }
            ]
            booking, _ = BookingService.book_tickets(
                user_id=test_user.id,
                flight_id=flight.id,
                passengers=passengers
            )
            # Mark as already paid
            booking.booking_status = BookingStatus.paid
            db.session.commit()
            booking_id = str(booking.id)

        # Try to pay again
        with app.app_context():
            token = UserService.generate_token(test_user)
            headers = {'Authorization': f'Bearer {token}'}

        response = client.post(
            '/api/payments/',
            json={
                'booking_number': booking_id,
                'credit_card_number': '1234567890123456',
                'security_code': '123'
            },
            headers=headers
        )

        assert response.status_code == 409
        assert 'already paid' in response.get_json()['message'].lower()

