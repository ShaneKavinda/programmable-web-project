"""
Pytest configuration and shared fixtures for tests.
"""

import pytest
import os
from datetime import datetime, timedelta, timezone
import jwt
os.environ.setdefault('ADMIN_API_KEY', 'test-admin-api-key')
from ticket_management_system import create_app
from ticket_management_system.extensions import db
from ticket_management_system.models import User
from ticket_management_system.resources.user_service import UserService


@pytest.fixture(scope='function')
def app():
    """Create application for testing with in-memory SQLite database."""
    # Use SQLite in-memory database for tests (isolated, doesn't affect real DB)
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['FLASK_ENV'] = 'testing'

    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Create all tables in the in-memory database
    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()



@pytest.fixture(scope='function')
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def test_user(app):
    """Create a test user for each test."""
    with app.app_context():
        user = User(
            firstname='Test',
            lastname='User',
            email='test@example.com',
        )
        db.session.add(user)
        db.session.commit()

        # Refresh to get the ID
        db.session.refresh(user)

        yield user


@pytest.fixture(scope='function')
def admin_user(app):
    """Create an admin user for each test."""
    with app.app_context():
        user = User(
            firstname='Admin',
            lastname='User',
            email='admin@test.com',
        )
        db.session.add(user)
        db.session.commit()

        db.session.refresh(user)

        yield user



@pytest.fixture(scope='function')
def auth_headers(app, test_user):
    """Generate authentication headers with valid token for regular user."""
    with app.app_context():
        token = UserService.generate_token(test_user)
        return {'Authorization': f'Bearer {token}'}


@pytest.fixture(scope='function')
def admin_headers(app, admin_user):
    """Generate headers with admin API key and bearer token."""
    with app.app_context():
        token = UserService.generate_token(admin_user)
        return {
            'x-api-key': os.environ['ADMIN_API_KEY'],
            'Authorization': f'Bearer {token}',
        }


@pytest.fixture(scope='function')
def expired_token(app, test_user):
    """Generate an expired JWT token."""
    with app.app_context():
        secret = os.getenv('JWT_SECRET_KEY', 'dummy-secret-key-for-development')
        payload = {
            'user_id': str(test_user.id),
            'email': test_user.email,
            'permitted_resources': UserService.get_permitted_resources(test_user),
            'exp': datetime.now(timezone.utc) - timedelta(hours=1),
            'iat': datetime.now(timezone.utc) - timedelta(hours=2)
        }
        return jwt.encode(payload, secret, algorithm='HS256')


@pytest.fixture(scope='function')
def multiple_users(app):
    """Create multiple users for pagination testing."""
    with app.app_context():
        users = []
        for i in range(5):
            user = User(
                firstname=f'User{i}',
                lastname=f'Test{i}',
                email=f'user{i}@test.com',
            )
            users.append(user)
            db.session.add(user)

        db.session.commit()

        # Get IDs
        user_ids = [u.id for u in users]

        yield users

        # Cleanup
        for user_id in user_ids:
            user = db.session.get(User, user_id)
            if user:
                db.session.delete(user)
        db.session.commit()


@pytest.fixture(scope='function')
def sample_flights(app):
    """Create sample flights for testing."""
    with app.app_context():
        from ticket_management_system.models import Flight, FlightStatus
        from decimal import Decimal
        from datetime import datetime
        import time

        flights = []
        unique_suffix = str(int(time.time() * 1000) % 10000)

        # Create a few sample flights with unique codes
        flight1 = Flight(
            flight_code=f'AA101_{unique_suffix}',
            origin_airport='JFK',
            destination_airport='LAX',
            departure_time=datetime(2026, 3, 15, 10, 0),
            arrival_time=datetime(2026, 3, 15, 14, 0),
            base_price=Decimal('299.99'),
            status=FlightStatus.active
        )

        flight2 = Flight(
            flight_code=f'UA202_{unique_suffix}',
            origin_airport='ORD',
            destination_airport='SFO',
            departure_time=datetime(2026, 3, 16, 12, 0),
            arrival_time=datetime(2026, 3, 16, 15, 30),
            base_price=Decimal('249.99'),
            status=FlightStatus.active
        )

        flights.extend([flight1, flight2])

        for flight in flights:
            db.session.add(flight)

        db.session.commit()

        yield flights



@pytest.fixture(scope='function')
def multiple_flights(app):
    """Create multiple flights for pagination testing."""
    with app.app_context():
        from ticket_management_system.models import Flight, FlightStatus
        from decimal import Decimal
        from datetime import datetime, timedelta

        # Clean up any existing flights with these codes first
        flight_codes = [f'FL{i+100}' for i in range(10)]
        Flight.query.filter(Flight.flight_code.in_(flight_codes)).delete(synchronize_session=False)
        db.session.commit()

        flights = []
        base_date = datetime(2026, 3, 15)

        for i in range(10):
            flight = Flight(
                flight_code=f'FL{i+100}',
                origin_airport=f'Airport_{i % 3}',
                destination_airport=f'Airport_{(i+1) % 3}',
                departure_time=base_date + timedelta(days=i),
                arrival_time=base_date + timedelta(days=i, hours=4),
                base_price=Decimal(f'{200 + i * 10}.99'),
                status=FlightStatus.active
            )
            flights.append(flight)
            db.session.add(flight)

        db.session.commit()

        # Get IDs
        flight_ids = [f.id for f in flights]

        yield flights

        # Cleanup
        for flight_id in flight_ids:
            flight = db.session.get(Flight, flight_id)
            if flight:
                db.session.delete(flight)
        db.session.commit()

