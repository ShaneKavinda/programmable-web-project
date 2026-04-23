"""
Unit tests for add flight endpoint.
Tests admin-only flight creation with validation.
"""

from datetime import datetime, timedelta
from ticket_management_system.extensions import db
from ticket_management_system.models import Flight


class TestAddFlightEndpoint:
    """Test POST /api/flights/ endpoint."""

    def test_add_flight_success_as_admin(self, client, app, admin_headers):
        """Test successful flight creation by admin."""
        with app.app_context():
            # Use a date far in the future to avoid timing issues
            future_date = datetime.now() + timedelta(days=30)
            flight_data = {
                'flight_code': 'TEST001',
                'origin_airport': 'JFK',
                'destination_airport': 'LAX',
                'departure_time': future_date.strftime('%Y-%m-%d %H:%M:%S'),
                'arrival_time': (future_date + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
                'base_price': 299.99
            }

            response = client.post('/api/flights/',
                                 json=flight_data,
                                 headers=admin_headers)

            assert response.status_code == 201
            data = response.get_json()

            assert 'message' in data
            assert 'Flight created successfully' in data['message']
            assert 'flight' in data
            assert data['flight']['flight_code'] == 'TEST001'
            assert data['flight']['status'] == 'active'

            # Cleanup
            flight = Flight.query.filter_by(flight_code='TEST001').first()
            if flight:
                db.session.delete(flight)
                db.session.commit()

    def test_add_flight_as_regular_user(self, client, app, auth_headers):
        """Test that bearer token alone cannot add flights without x-api-key."""
        with app.app_context():
            future_date = datetime.now() + timedelta(days=30)
            flight_data = {
                'flight_code': 'TEST002',
                'origin_airport': 'JFK',
                'destination_airport': 'LAX',
                'departure_time': future_date.strftime('%Y-%m-%d %H:%M:%S'),
                'arrival_time': (future_date + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
                'base_price': 299.99
            }

            response = client.post('/api/flights/',
                                 json=flight_data,
                                 headers=auth_headers)

            assert response.status_code == 401
            data = response.get_json()
            assert 'error' in data
            assert 'Unauthorized' in data['error']

    def test_add_flight_without_auth(self, client, app):
        """Test that unauthenticated requests are rejected."""
        with app.app_context():
            future_date = datetime.now() + timedelta(days=30)
            flight_data = {
                'flight_code': 'TEST003',
                'origin_airport': 'JFK',
                'destination_airport': 'LAX',
                'departure_time': future_date.strftime('%Y-%m-%d %H:%M:%S'),
                'arrival_time': (future_date + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
                'base_price': 299.99
            }

            response = client.post('/api/flights/', json=flight_data)

            assert response.status_code == 401

    def test_add_flight_missing_fields(self, client, app, admin_headers):
        """Test validation error for missing required fields."""
        with app.app_context():
            flight_data = {
                'flight_code': 'TEST004',
                'origin_airport': 'JFK'
                # Missing other required fields
            }

            response = client.post('/api/flights/',
                                 json=flight_data,
                                 headers=admin_headers)

            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data
            assert 'destination_airport' in data['errors']
            assert 'departure_time' in data['errors']

    def test_add_flight_departure_in_past(self, client, app, admin_headers):
        """Test validation error for departure time in past."""
        with app.app_context():
            past_date = datetime.now() - timedelta(days=1)
            flight_data = {
                'flight_code': 'TEST005',
                'origin_airport': 'JFK',
                'destination_airport': 'LAX',
                'departure_time': past_date.strftime('%Y-%m-%d %H:%M:%S'),
                'arrival_time': (past_date + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
                'base_price': 299.99
            }

            response = client.post('/api/flights/',
                                 json=flight_data,
                                 headers=admin_headers)

            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data
            assert 'departure_time' in data['errors']

    def test_add_flight_arrival_before_departure(self, client, app, admin_headers):
        """Test validation error for arrival before departure."""
        with app.app_context():
            future_date = datetime.now() + timedelta(days=30)
            flight_data = {
                'flight_code': 'TEST006',
                'origin_airport': 'JFK',
                'destination_airport': 'LAX',
                'departure_time': future_date.strftime('%Y-%m-%d %H:%M:%S'),
                'arrival_time': (future_date - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'base_price': 299.99
            }

            response = client.post('/api/flights/',
                                 json=flight_data,
                                 headers=admin_headers)

            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data
            assert 'arrival_time' in data['errors']

    def test_add_flight_same_origin_destination(self, client, app, admin_headers):
        """Test validation error for same origin and destination."""
        with app.app_context():
            future_date = datetime.now() + timedelta(days=30)
            flight_data = {
                'flight_code': 'TEST007',
                'origin_airport': 'JFK',
                'destination_airport': 'JFK',  # Same as origin
                'departure_time': future_date.strftime('%Y-%m-%d %H:%M:%S'),
                'arrival_time': (future_date + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
                'base_price': 299.99
            }

            response = client.post('/api/flights/',
                                 json=flight_data,
                                 headers=admin_headers)

            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data
            assert 'destination_airport' in data['errors']

    def test_add_flight_duplicate_code(self, client, app, admin_headers):
        """Test error for duplicate flight code."""
        with app.app_context():
            # Create first flight
            future_date = datetime.now() + timedelta(days=30)
            flight_data = {
                'flight_code': 'DUP001',
                'origin_airport': 'JFK',
                'destination_airport': 'LAX',
                'departure_time': future_date.strftime('%Y-%m-%d %H:%M:%S'),
                'arrival_time': (future_date + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
                'base_price': 299.99
            }

            response1 = client.post('/api/flights/',
                                  json=flight_data,
                                  headers=admin_headers)
            assert response1.status_code == 201

            # Try to create duplicate
            response2 = client.post('/api/flights/',
                                  json=flight_data,
                                  headers=admin_headers)

            assert response2.status_code == 409
            data = response2.get_json()
            assert 'error' in data
            assert 'Conflict' in data['error']
            assert 'already exists' in data['message']

            # Cleanup
            flight = Flight.query.filter_by(flight_code='DUP001').first()
            if flight:
                db.session.delete(flight)
                db.session.commit()

    def test_add_flight_invalid_price(self, client, app, admin_headers):
        """Test validation error for negative price."""
        with app.app_context():
            future_date = datetime.now() + timedelta(days=30)
            flight_data = {
                'flight_code': 'TEST008',
                'origin_airport': 'JFK',
                'destination_airport': 'LAX',
                'departure_time': future_date.strftime('%Y-%m-%d %H:%M:%S'),
                'arrival_time': (future_date + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
                'base_price': -100
            }

            response = client.post('/api/flights/',
                                 json=flight_data,
                                 headers=admin_headers)

            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data
            assert 'base_price' in data['errors']

    def test_add_flight_flight_code_uppercase(self, client, app, admin_headers):
        """Test that flight code is converted to uppercase."""
        with app.app_context():
            future_date = datetime.now() + timedelta(days=30)
            flight_data = {
                'flight_code': 'test999',  # lowercase
                'origin_airport': 'JFK',
                'destination_airport': 'LAX',
                'departure_time': future_date.strftime('%Y-%m-%d %H:%M:%S'),
                'arrival_time': (future_date + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
                'base_price': 299.99
            }

            response = client.post('/api/flights/',
                                 json=flight_data,
                                 headers=admin_headers)

            assert response.status_code == 201
            data = response.get_json()
            assert data['flight']['flight_code'] == 'TEST999'  # uppercase

            # Cleanup
            flight = Flight.query.filter_by(flight_code='TEST999').first()
            if flight:
                db.session.delete(flight)
                db.session.commit()

    def test_add_flight_returns_json(self, client, app, admin_headers):
        """Test that response content type is JSON."""
        with app.app_context():
            future_date = datetime.now() + timedelta(days=30)
            flight_data = {
                'flight_code': 'TEST010',
                'origin_airport': 'JFK',
                'destination_airport': 'LAX',
                'departure_time': future_date.strftime('%Y-%m-%d %H:%M:%S'),
                'arrival_time': (future_date + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
                'base_price': 299.99
            }

            response = client.post('/api/flights/',
                                 json=flight_data,
                                 headers=admin_headers)

            assert response.content_type == 'application/json'

            # Cleanup
            flight = Flight.query.filter_by(flight_code='TEST010').first()
            if flight:
                db.session.delete(flight)
                db.session.commit()
