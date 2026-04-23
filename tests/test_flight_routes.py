"""
Unit tests for flight routes endpoints.
Tests all HTTP endpoints in the flight routes blueprint.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from ticket_management_system.extensions import db
from ticket_management_system.models import Booking, BookingStatus, Flight, FlightStatus


class TestAirportsEndpoint:
    """Test GET /api/flights/airports endpoint."""

    def test_get_airports_empty_database(self, client, app, auth_headers):
        """Test getting airports when no flights exist."""
        with app.app_context():
            # Clean up all flights first
            Flight.query.delete()
            db.session.commit()

            response = client.get('/api/flights/airports', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert 'airports' in data
            assert 'count' in data
            assert data['count'] == 0
            assert data['airports'] == []

    def test_get_airports_with_flights(self, client, app, sample_flights, auth_headers):
        """Test getting airports with flights in database."""
        with app.app_context():
            response = client.get('/api/flights/airports', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert data['count'] > 0
            assert len(data['airports']) == data['count']
            assert isinstance(data['airports'], list)

    def test_get_airports_returns_json(self, client, app, sample_flights, auth_headers):
        """Test that response content type is JSON."""
        with app.app_context():
            response = client.get('/api/flights/airports', headers=auth_headers)

            assert response.content_type == 'application/json'

    def test_get_airports_distinct_values(self, client, app, auth_headers):
        """Test that airports list has no duplicates."""
        with app.app_context():
            # Create flights with duplicate airports
            flight1 = Flight(
                flight_code='AA101',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            flight2 = Flight(
                flight_code='AA102',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 16, 10, 0),
                arrival_time=datetime(2026, 3, 16, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight1)
            db.session.add(flight2)
            db.session.commit()

            response = client.get('/api/flights/airports', headers=auth_headers)
            data = response.get_json()

            # Should only return unique airports
            airports_set = set(data['airports'])
            assert len(airports_set) == len(data['airports'])

            # Cleanup
            db.session.delete(flight1)
            db.session.delete(flight2)
            db.session.commit()

    def test_get_airports_sorted(self, client, app, auth_headers):
        """Test that airports are returned in sorted order."""
        with app.app_context():
            # Create flights with various airports
            flight1 = Flight(
                flight_code='AA101',
                origin_airport='ORD',
                destination_airport='ATL',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('199.99'),
                status=FlightStatus.active
            )
            db.session.add(flight1)
            db.session.commit()

            response = client.get('/api/flights/airports', headers=auth_headers)
            data = response.get_json()

            # Check if sorted
            assert data['airports'] == sorted(data['airports'])

            # Cleanup
            db.session.delete(flight1)
            db.session.commit()

    def test_get_airports_without_auth(self, client, app):
        """Airports endpoint is public."""
        with app.app_context():
            response = client.get('/api/flights/airports')

            assert response.status_code == 200


class TestFlightSearchEndpoint:
    """Test GET /api/flights/search endpoint."""

    def test_search_flights_no_parameters(self, client, app, sample_flights, auth_headers):
        """Test search without any query parameters."""
        with app.app_context():
            response = client.get('/api/flights/search', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert 'flights' in data
            assert 'pagination' in data
            assert isinstance(data['flights'], list)

    def test_search_flights_by_origin(self, client, app, auth_headers):
        """Test search by origin airport."""
        with app.app_context():
            flight = Flight(
                flight_code='AA_ORIGIN_001',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            response = client.get('/api/flights/search?origin_airport=JFK', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert len(data['flights']) > 0
            for f in data['flights']:
                assert 'JFK' in f['origin_airport']

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_search_flights_by_destination(self, client, app, auth_headers):
        """Test search by destination airport."""
        with app.app_context():
            flight = Flight(
                flight_code='AA_DEST_001',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            response = client.get('/api/flights/search?destination_airport=LAX', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert len(data['flights']) > 0
            for f in data['flights']:
                assert 'LAX' in f['destination_airport']

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_search_flights_by_both_airports(self, client, app, auth_headers):
        """Test search by both origin and destination."""
        with app.app_context():
            flight = Flight(
                flight_code='AA_BOTH_001',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            response = client.get(
                '/api/flights/search?origin_airport=JFK&destination_airport=LAX',
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.get_json()

            assert len(data['flights']) > 0
            for f in data['flights']:
                assert 'JFK' in f['origin_airport']
                assert 'LAX' in f['destination_airport']

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_search_flights_by_departure_date(self, client, app, auth_headers):
        """Test search by departure date."""
        with app.app_context():
            flight = Flight(
                flight_code='AA_DEPT_001',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            response = client.get('/api/flights/search?departure_date=2026-03-15', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            # If flights found, check they're on the right date
            for f in data['flights']:
                departure = datetime.fromisoformat(f['departure_time'])
                assert departure.date().isoformat() == '2026-03-15'

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_search_flights_by_arrival_date(self, client, app, auth_headers):
        """Test search by arrival date."""
        with app.app_context():
            flight = Flight(
                flight_code='AA_ARR_001',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            response = client.get('/api/flights/search?arrival_date=2026-03-15', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_search_flights_complex_query(self, client, app, auth_headers):
        """Test search with multiple filters."""
        with app.app_context():
            flight = Flight(
                flight_code='AA_CMPLX_001',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            response = client.get(
                '/api/flights/search?'
                'origin_airport=JFK&'
                'destination_airport=LAX&'
                'departure_date=2026-03-15',
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.get_json()

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_search_flights_with_pagination(self, client, app, multiple_flights, auth_headers):
        """Test search with pagination parameters."""
        with app.app_context():
            response = client.get('/api/flights/search?page=1&per_page=5', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert data['pagination']['page'] == 1
            assert data['pagination']['per_page'] == 5
            assert len(data['flights']) <= 5

    def test_search_flights_second_page(self, client, app, multiple_flights, auth_headers):
        """Test getting second page of results."""
        with app.app_context():
            response = client.get('/api/flights/search?page=2&per_page=3', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert data['pagination']['page'] == 2

    def test_search_flights_sort_by_price_desc(self, client, app, multiple_flights, auth_headers):
        """Test sort_by base_price with sort_order desc (highest price first)."""
        with app.app_context():
            response = client.get(
                '/api/flights/search?sort_by=base_price&sort_order=desc&per_page=1',
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.get_json()
            assert len(data['flights']) == 1
            assert data['flights'][0]['flight_code'] == 'FL109'

    def test_search_flights_sort_invalid_sort_by(self, client, app, sample_flights, auth_headers):
        """Invalid sort_by returns validation error."""
        with app.app_context():
            response = client.get('/api/flights/search?sort_by=not_a_column', headers=auth_headers)
            assert response.status_code == 400

    def test_search_flights_no_results(self, client, app, auth_headers):
        """Test search that returns no results."""
        with app.app_context():
            response = client.get('/api/flights/search?origin_airport=NONEXISTENT', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert data['flights'] == []
            assert data['pagination']['total_items'] == 0

    def test_search_flights_invalid_date_format(self, client, app, sample_flights, auth_headers):
        """Test search with invalid date format."""
        with app.app_context():
            response = client.get('/api/flights/search?departure_date=invalid-date', headers=auth_headers)

            # Should return 400 Bad Request with Marshmallow error format
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
            assert 'Bad Request' in data['error']
            assert 'message' in data
            assert 'errors' in data  # Marshmallow returns errors dict
            assert 'departure_date' in data['errors']  # Field-specific error

    def test_search_flights_invalid_arrival_date_format(self, client, app, auth_headers):
        """Test search with invalid arrival date format."""
        with app.app_context():
            response = client.get('/api/flights/search?arrival_date=2026/02/08', headers=auth_headers)

            # Should return 400 Bad Request
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
            assert 'errors' in data
            assert 'arrival_date' in data['errors']

    def test_search_flights_valid_date_formats(self, client, app, auth_headers):
        """Test search with valid date formats."""
        with app.app_context():
            # All these should return 200 (even if no results)
            # Use future dates to pass Marshmallow validation
            response1 = client.get('/api/flights/search?departure_date=2026-12-15', headers=auth_headers)
            response2 = client.get('/api/flights/search?arrival_date=2026-12-31', headers=auth_headers)
            response3 = client.get('/api/flights/search?departure_date=2026-12-01&arrival_date=2026-12-01', headers=auth_headers)

            assert response1.status_code == 200
            assert response2.status_code == 200
            assert response3.status_code == 200

    def test_search_flights_partial_invalid_dates(self, client, app, auth_headers):
        """Test search with partially invalid dates."""
        with app.app_context():
            # Invalid month
            response1 = client.get('/api/flights/search?departure_date=2026-13-01', headers=auth_headers)
            assert response1.status_code == 400

            # Invalid day
            response2 = client.get('/api/flights/search?departure_date=2026-02-30', headers=auth_headers)
            assert response2.status_code == 400

            # Wrong format
            response3 = client.get('/api/flights/search?departure_date=08-02-2026', headers=auth_headers)
            assert response3.status_code == 400

    def test_search_flights_returns_json(self, client, app, sample_flights, auth_headers):
        """Test that response content type is JSON."""
        with app.app_context():
            response = client.get('/api/flights/search', headers=auth_headers)

            assert response.content_type == 'application/json'

    def test_search_flights_without_auth(self, client, app):
        """Search endpoint is public."""
        with app.app_context():
            response = client.get('/api/flights/search')

            assert response.status_code == 200


class TestFlightSearchPagination:
    """Test pagination functionality in search endpoint."""

    def test_search_custom_page_size(self, client, app, multiple_flights, auth_headers):
        """Test custom page size."""
        with app.app_context():
            response = client.get('/api/flights/search?per_page=20', headers=auth_headers)
            data = response.get_json()

            assert data['pagination']['per_page'] == 20

    def test_search_pagination_metadata(self, client, app, multiple_flights, auth_headers):
        """Test pagination metadata presence."""
        with app.app_context():
            response = client.get('/api/flights/search', headers=auth_headers)
            data = response.get_json()

            pagination = data['pagination']
            assert 'page' in pagination
            assert 'per_page' in pagination
            assert 'total_pages' in pagination
            assert 'total_items' in pagination
            assert 'has_next' in pagination
            assert 'has_prev' in pagination
            assert 'next_page' in pagination
            assert 'prev_page' in pagination

    def test_search_first_page_no_prev(self, client, app, multiple_flights, auth_headers):
        """Test that first page has no previous page."""
        with app.app_context():
            response = client.get('/api/flights/search?page=1', headers=auth_headers)
            data = response.get_json()

            assert data['pagination']['has_prev'] is False
            assert data['pagination']['prev_page'] is None

    def test_search_navigation_links(self, client, app, multiple_flights, auth_headers):
        """Test pagination navigation links."""
        with app.app_context():
            response = client.get('/api/flights/search?page=2&per_page=3', headers=auth_headers)
            data = response.get_json()

            pagination = data['pagination']
            if pagination['has_prev']:
                assert pagination['prev_page'] == 1
            if pagination['has_next']:
                assert pagination['next_page'] == 3


class TestFlightSearchEdgeCases:
    """Test edge cases and error scenarios."""

    def test_search_empty_database(self, client, app, auth_headers):
        """Test search when database is empty."""
        with app.app_context():
            # Clean up all flights first
            Flight.query.delete()
            db.session.commit()

            response = client.get('/api/flights/search', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert data['flights'] == []
            assert data['pagination']['total_items'] == 0

    def test_search_special_characters_in_query(self, client, app, auth_headers):
        """Test search with special characters."""
        with app.app_context():
            response = client.get('/api/flights/search?origin_airport=%20test%20', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()
            assert 'flights' in data

    def test_search_negative_page_number(self, client, app, sample_flights, auth_headers):
        """Test search with negative page number."""
        with app.app_context():
            response = client.get('/api/flights/search?page=-1', headers=auth_headers)

            # Marshmallow validates and rejects negative page numbers
            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data
            assert 'page' in data['errors']

    def test_search_zero_per_page(self, client, app, sample_flights, auth_headers):
        """Test search with zero per_page."""
        with app.app_context():
            response = client.get('/api/flights/search?per_page=0', headers=auth_headers)

            # Marshmallow validates and rejects zero per_page
            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data
            assert 'per_page' in data['errors']

    def test_search_excessive_per_page(self, client, app, sample_flights, auth_headers):
        """Test search with per_page exceeding maximum."""
        with app.app_context():
            response = client.get('/api/flights/search?per_page=500', headers=auth_headers)

            # Marshmallow validates and rejects excessive per_page
            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data
            assert 'per_page' in data['errors']


class TestGetFlightByIdEndpoint:
    """Test GET /api/flights/{id} endpoint."""

    def test_get_flight_by_id(self, client, app, auth_headers):
        """Test getting a flight by its UUID."""
        with app.app_context():
            flight = Flight(
                flight_code='GETTEST001',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()
            flight_id = flight.id

            response = client.get(f'/api/flights/{flight_id}', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()
            assert 'flight' in data
            assert data['flight']['id'] == str(flight_id)
            assert data['flight']['flight_code'] == 'GETTEST001'
            assert data['flight']['origin_airport'] == 'JFK'
            assert data['flight']['destination_airport'] == 'LAX'
            assert data['flight']['status'] == 'active'

            db.session.delete(flight)
            db.session.commit()

    def test_get_flight_by_id_response_structure(self, client, app, auth_headers):
        """Test that response has all expected fields."""
        with app.app_context():
            flight = Flight(
                flight_code='GETTEST002',
                origin_airport='ORD',
                destination_airport='SFO',
                departure_time=datetime(2026, 5, 20, 8, 0),
                arrival_time=datetime(2026, 5, 20, 11, 0),
                base_price=Decimal('199.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()
            flight_id = flight.id

            response = client.get(f'/api/flights/{flight_id}', headers=auth_headers)

            assert response.status_code == 200
            flight_data = response.get_json()['flight']
            assert 'id' in flight_data
            assert 'flight_code' in flight_data
            assert 'origin_airport' in flight_data
            assert 'destination_airport' in flight_data
            assert 'departure_time' in flight_data
            assert 'arrival_time' in flight_data
            assert 'base_price' in flight_data
            assert 'status' in flight_data
            assert 'created_at' in flight_data
            assert 'updated_at' in flight_data

            db.session.delete(flight)
            db.session.commit()

    def test_get_flight_include_bookings_query_param(self, client, app, auth_headers, test_user):
        """GET /api/flights/{id}?include_bookings=true embeds booking id/user/status."""
        with app.app_context():
            flight = Flight(
                flight_code='BKEMBED01',
                origin_airport='HEL',
                destination_airport='RIX',
                departure_time=datetime(2026, 6, 1, 10, 0),
                arrival_time=datetime(2026, 6, 1, 11, 30),
                base_price=Decimal('120.00'),
                status=FlightStatus.active,
            )
            db.session.add(flight)
            db.session.flush()
            booking = Booking(
                user_id=test_user.id,
                flight_id=flight.id,
                total_price=Decimal('120.00'),
                booking_status=BookingStatus.booked,
            )
            db.session.add(booking)
            db.session.commit()
            flight_id = flight.id
            booking_id = booking.id

        response = client.get(
            f'/api/flights/{flight_id}?include_bookings=true',
            headers=auth_headers,
        )
        assert response.status_code == 200
        flight_data = response.get_json()['flight']
        assert 'bookings' in flight_data
        assert len(flight_data['bookings']) == 1
        assert flight_data['bookings'][0]['id'] == str(booking_id)
        assert flight_data['bookings'][0]['user_id'] == str(test_user.id)
        assert flight_data['bookings'][0]['booking_status'] == 'booked'

        with app.app_context():
            db.session.delete(db.session.get(Booking, booking_id))
            db.session.delete(db.session.get(Flight, flight_id))
            db.session.commit()

    def test_get_flight_not_found(self, client, app, auth_headers):
        """Test getting a flight that doesn't exist."""
        with app.app_context():
            import uuid
            nonexistent_id = uuid.uuid4()

            response = client.get(f'/api/flights/{nonexistent_id}', headers=auth_headers)

            assert response.status_code == 404
            data = response.get_json()
            assert data['error'] == 'Not Found'
            assert 'not found' in data['message']

    def test_get_flight_invalid_uuid(self, client, app, auth_headers):
        """Test getting a flight with invalid UUID format."""
        with app.app_context():
            response = client.get('/api/flights/not-a-valid-uuid', headers=auth_headers)
            assert response.status_code == 404

    def test_get_flight_without_auth(self, client, app):
        """Get-flight endpoint is public and returns 404 for unknown id."""
        with app.app_context():
            import uuid
            fake_id = uuid.uuid4()
            response = client.get(f'/api/flights/{fake_id}')

            assert response.status_code == 404

    def test_get_flight_with_invalid_token(self, client, app):
        """Invalid bearer token is ignored for this public endpoint."""
        with app.app_context():
            import uuid
            fake_id = uuid.uuid4()
            response = client.get(
                f'/api/flights/{fake_id}',
                headers={'Authorization': 'Bearer invalid_token'}
            )
            assert response.status_code == 404

    def test_get_flight_unexpected_exception(self, client, app, auth_headers):
        """Test get_flight handles unexpected exceptions."""
        with app.app_context():
            import uuid
            flight_id = uuid.uuid4()

            with patch('ticket_management_system.resources.flights.FlightService.get_flight_by_id') as mock_service:
                mock_service.side_effect = Exception('Database error')

                response = client.get(f'/api/flights/{flight_id}', headers=auth_headers)

                assert response.status_code == 500
                data = response.get_json()
                assert 'error' in data
                assert 'Internal Server Error' in data['error']


class TestUpdateFlightEndpoint:
    """Test PUT /api/flights/{id} endpoint."""

    def test_update_flight_as_admin(self, client, app, admin_headers):
        """Test updating a flight as admin."""
        with app.app_context():
            # Create a test flight
            test_flight = Flight(
                flight_code='TESTUPD001',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            # Update the flight
            update_data = {
                'base_price': 399.99
            }
            response = client.put(
                f'/api/flights/{flight_id}',
                json=update_data,
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.get_json()
            assert 'message' in data
            assert 'Flight updated successfully' in data['message']
            assert 'flight' in data
            assert str(data['flight']['base_price']) == '399.99'

            # Verify in database
            updated_flight = Flight.query.filter_by(id=flight_id).first()
            assert updated_flight.base_price == Decimal('399.99')

            # Cleanup
            db.session.delete(updated_flight)
            db.session.commit()

    def test_update_flight_origin_airport(self, client, app, admin_headers):
        """Test updating only the origin airport."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD002',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            response = client.put(
                f'/api/flights/{flight_id}',
                json={'origin_airport': 'ORD'},
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['flight']['origin_airport'] == 'ORD'

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_flight_destination_airport(self, client, app, admin_headers):
        """Test updating only the destination airport."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD003',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            response = client.put(
                f'/api/flights/{flight_id}',
                json={'destination_airport': 'SFO'},
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['flight']['destination_airport'] == 'SFO'

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_flight_departure_time(self, client, app, admin_headers):
        """Test updating departure time."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD004',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            new_departure = datetime(2026, 5, 20, 12, 30)
            response = client.put(
                f'/api/flights/{flight_id}',
                json={'departure_time': new_departure.strftime('%Y-%m-%d %H:%M:%S')},
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.get_json()
            # Verify the departure time was updated
            assert '2026-05-20' in data['flight']['departure_time']

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_flight_arrival_time(self, client, app, admin_headers):
        """Test updating arrival time."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD005',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            new_arrival = datetime(2026, 5, 20, 17, 30)
            response = client.put(
                f'/api/flights/{flight_id}',
                json={'arrival_time': new_arrival.strftime('%Y-%m-%d %H:%M:%S')},
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.get_json()
            assert '2026-05-20' in data['flight']['arrival_time']

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_flight_multiple_fields(self, client, app, admin_headers):
        """Test updating multiple fields at once."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD006',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            new_departure = datetime(2026, 5, 20, 12, 30)
            new_arrival = datetime(2026, 5, 20, 17, 30)
            response = client.put(
                f'/api/flights/{flight_id}',
                json={
                    'origin_airport': 'ORD',
                    'destination_airport': 'SFO',
                    'base_price': 499.99,
                    'departure_time': new_departure.strftime('%Y-%m-%d %H:%M:%S'),
                    'arrival_time': new_arrival.strftime('%Y-%m-%d %H:%M:%S')
                },
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['flight']['origin_airport'] == 'ORD'
            assert data['flight']['destination_airport'] == 'SFO'
            assert str(data['flight']['base_price']) == '499.99'

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_flight_as_regular_user(self, client, app, auth_headers):
        """Bearer token alone cannot update without x-api-key."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD007',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            response = client.put(
                f'/api/flights/{flight_id}',
                json={'base_price': 399.99},
                headers=auth_headers
            )

            assert response.status_code == 401
            data = response.get_json()
            assert data['error'] == 'Unauthorized'

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_nonexistent_flight(self, client, app, admin_headers):
        """Test updating a flight that doesn't exist."""
        with app.app_context():
            import uuid
            nonexistent_id = uuid.uuid4()

            response = client.put(
                f'/api/flights/{nonexistent_id}',
                json={'base_price': 399.99},
                headers=admin_headers
            )

            assert response.status_code == 404
            data = response.get_json()
            assert data['error'] == 'Not Found'

    def test_update_flight_without_token(self, client, app):
        """Test updating a flight without authentication."""
        with app.app_context():
            import uuid
            fake_id = uuid.uuid4()
            response = client.put(
                f'/api/flights/{fake_id}',
                json={'base_price': 399.99}
            )

            assert response.status_code == 401
            data = response.get_json()
            assert 'error' in data

    def test_update_flight_with_invalid_token(self, client, app):
        """Test updating a flight with invalid token."""
        with app.app_context():
            import uuid
            fake_id = uuid.uuid4()
            response = client.put(
                f'/api/flights/{fake_id}',
                json={'base_price': 399.99},
                headers={'Authorization': 'Bearer invalid_token'}
            )

            assert response.status_code == 401

    def test_update_flight_no_fields_provided(self, client, app, admin_headers):
        """Test update with empty request body (no fields to update)."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD008',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            response = client.put(
                f'/api/flights/{flight_id}',
                json={},
                headers=admin_headers
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
            assert 'Bad Request' in data['error']

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_flight_invalid_origin_length(self, client, app, admin_headers):
        """Test update with origin airport too short."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD009',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            response = client.put(
                f'/api/flights/{flight_id}',
                json={'origin_airport': 'JK'},  # Too short
                headers=admin_headers
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_flight_same_origin_destination(self, client, app, admin_headers):
        """Test update with same origin and destination."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD010',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            response = client.put(
                f'/api/flights/{flight_id}',
                json={
                    'origin_airport': 'JFK',
                    'destination_airport': 'JFK'  # Same as origin
                },
                headers=admin_headers
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data
            assert 'destination_airport' in data['errors']

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_flight_arrival_before_departure(self, client, app, admin_headers):
        """Test update with arrival time before departure time."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD011',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            response = client.put(
                f'/api/flights/{flight_id}',
                json={
                    'departure_time': '2026-05-20 15:00:00',
                    'arrival_time': '2026-05-20 10:00:00'  # Before departure
                },
                headers=admin_headers
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data
            assert 'arrival_time' in data['errors']

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_flight_invalid_date_format(self, client, app, admin_headers):
        """Test update with invalid date format."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD012',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            response = client.put(
                f'/api/flights/{flight_id}',
                json={'departure_time': 'invalid-date'},
                headers=admin_headers
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_flight_negative_price(self, client, app, admin_headers):
        """Test update with negative price."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD013',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            response = client.put(
                f'/api/flights/{flight_id}',
                json={'base_price': -99.99},
                headers=admin_headers
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_flight_response_structure(self, client, app, admin_headers):
        """Test that update response has correct structure."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD014',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            response = client.put(
                f'/api/flights/{flight_id}',
                json={'base_price': 399.99},
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.get_json()

            # Check response structure
            assert 'message' in data
            assert 'flight' in data

            # Check flight object structure
            flight = data['flight']
            assert 'id' in flight
            assert 'flight_code' in flight
            assert 'origin_airport' in flight
            assert 'destination_airport' in flight
            assert 'departure_time' in flight
            assert 'arrival_time' in flight
            assert 'base_price' in flight
            assert 'status' in flight
            assert 'created_at' in flight
            assert 'updated_at' in flight

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

    def test_update_flight_past_time_not_allowed(self, client, app, admin_headers):
        """Test that updating with past time is not allowed."""
        with app.app_context():
            test_flight = Flight(
                flight_code='TESTUPD015',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            # Try to update with a past date
            past_date = datetime(2020, 1, 1, 10, 0)
            response = client.put(
                f'/api/flights/{flight_id}',
                json={'departure_time': past_date.strftime('%Y-%m-%d %H:%M:%S')},
                headers=admin_headers
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data

            # Cleanup
            db.session.delete(Flight.query.filter_by(id=flight_id).first())
            db.session.commit()

class TestFlightRoutesIntegration:
    """Integration tests for flight routes."""

    def test_airports_then_search_workflow(self, client, app, auth_headers):
        """Test typical user workflow: get airports, then search."""
        with app.app_context():
            # Create a flight
            flight = Flight(
                flight_code='AA_WORKFLOW_001',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            # Step 1: Get available airports
            airports_response = client.get('/api/flights/airports', headers=auth_headers)
            airports_data = airports_response.get_json()

            assert airports_response.status_code == 200
            assert len(airports_data['airports']) > 0

            # Step 2: Use one of the airports to search
            first_airport = airports_data['airports'][0]
            search_response = client.get(
                f'/api/flights/search?origin_airport={first_airport}',
                headers=auth_headers
            )
            search_data = search_response.get_json()

            assert search_response.status_code == 200
            assert 'flights' in search_data

            # Cleanup
            db.session.delete(flight)
            db.session.commit()


class TestDeleteFlightEndpoint:
    """Test DELETE /api/flights/{id} endpoint."""

    def test_delete_flight_as_admin(self, client, app, admin_headers):
        """Test deleting a flight as admin."""
        with app.app_context():
            # Create a test flight
            test_flight = Flight(
                flight_code='TESTDEL001',
                origin_airport='NYC',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('500.00'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            # Delete the flight
            response = client.delete(f'/api/flights/{flight_id}',
                headers=admin_headers)

            assert response.status_code == 200
            data = response.get_json()
            assert 'message' in data
            assert 'deleted successfully' in data['message']

            # Verify flight is deleted
            deleted_flight = Flight.query.filter_by(id=flight_id).first()
            assert deleted_flight is None

    def test_delete_flight_as_regular_user(self, client, app, auth_headers):
        """Bearer token alone cannot delete without x-api-key."""
        with app.app_context():
            # Create a test flight
            test_flight = Flight(
                flight_code='TESTDEL002',
                origin_airport='NYC',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('500.00'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            # Try to delete as regular user
            response = client.delete(f'/api/flights/{flight_id}',
                headers=auth_headers)

            assert response.status_code == 401
            data = response.get_json()
            assert data['error'] == 'Unauthorized'

            # Verify flight still exists
            flight_still_exists = Flight.query.filter_by(id=flight_id).first()
            assert flight_still_exists is not None

            # Cleanup
            db.session.delete(flight_still_exists)
            db.session.commit()

    def test_delete_nonexistent_flight(self, client, app, admin_headers):
        """Test deleting a flight that doesn't exist."""
        with app.app_context():
            import uuid
            # Use a random UUID that doesn't exist
            nonexistent_id = uuid.uuid4()

            response = client.delete(f'/api/flights/{nonexistent_id}',
                headers=admin_headers)

            assert response.status_code == 404
            data = response.get_json()
            assert data['error'] == 'Not Found'
            assert 'not found' in data['message']

    def test_delete_flight_without_token(self, client, app):
        """Deleting without x-api-key should fail with unauthorized."""
        with app.app_context():
            import uuid
            fake_id = uuid.uuid4()
            response = client.delete(f'/api/flights/{fake_id}')

            assert response.status_code == 401
            data = response.get_json()
            assert data['error'] == 'Unauthorized'

    def test_delete_flight_with_invalid_token(self, client, app):
        """Test deleting a flight with invalid token."""
        with app.app_context():
            import uuid
            fake_id = uuid.uuid4()
            response = client.delete(f'/api/flights/{fake_id}',
                headers={'Authorization': 'Bearer invalid_token'})

            assert response.status_code == 401

    def test_delete_flight_invalid_uuid_format(self, client, app, admin_headers):
        """Test deleting a flight with invalid UUID format."""
        with app.app_context():
            response = client.delete('/api/flights/not-a-valid-uuid',
                headers=admin_headers)

            # Flask will return 404 for invalid UUID format
            assert response.status_code == 404

    def test_delete_flight_cascades_bookings(self, client, app, admin_headers, test_user):
        """Test that deleting a flight cascades to delete related bookings."""
        with app.app_context():
            from ticket_management_system.models import Booking, BookingStatus

            # Create a test flight
            test_flight = Flight(
                flight_code='TESTCAS001',
                origin_airport='NYC',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('500.00'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            # Create a booking for this flight
            test_booking = Booking(
                user_id=test_user.id,
                flight_id=flight_id,
                total_price=Decimal('500.00'),
                booking_status=BookingStatus.booked
            )
            db.session.add(test_booking)
            db.session.commit()
            booking_id = test_booking.id

            # Delete the flight
            response = client.delete(f'/api/flights/{flight_id}',
                headers=admin_headers)

            assert response.status_code == 200

            # Verify flight is deleted
            deleted_flight = Flight.query.filter_by(id=flight_id).first()
            assert deleted_flight is None

            # Verify booking is also deleted (cascade)
            deleted_booking = Booking.query.filter_by(id=booking_id).first()
            assert deleted_booking is None

    def test_delete_flight_cascades_tickets(self, client, app, admin_headers, test_user):
        """Test that deleting a flight cascades to delete related tickets."""
        with app.app_context():
            from ticket_management_system.models import Booking, Ticket, BookingStatus, SeatClass

            # Create a test flight
            test_flight = Flight(
                flight_code='TESTCAS002',
                origin_airport='NYC',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('500.00'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            # Create a booking
            test_booking = Booking(
                user_id=test_user.id,
                flight_id=flight_id,
                total_price=Decimal('500.00'),
                booking_status=BookingStatus.booked
            )
            db.session.add(test_booking)
            db.session.commit()

            # Create a ticket
            test_ticket = Ticket(
                booking_id=test_booking.id,
                flight_id=flight_id,
                passenger_name='John Doe',
                passenger_passport_num='AB123456',
                seat_num='12A',
                price=Decimal('500.00'),
                seat_class=SeatClass.economy
            )
            db.session.add(test_ticket)
            db.session.commit()
            ticket_id = test_ticket.id

            # Delete the flight
            response = client.delete(f'/api/flights/{flight_id}',
                headers=admin_headers)

            assert response.status_code == 200

            # Verify ticket is also deleted (cascade)
            deleted_ticket = Ticket.query.filter_by(id=ticket_id).first()
            assert deleted_ticket is None

    def test_delete_flight_response_structure(self, client, app, admin_headers):
        """Test that delete response has correct structure."""
        with app.app_context():
            # Create a test flight
            test_flight = Flight(
                flight_code='TESTRES001',
                origin_airport='NYC',
                destination_airport='LAX',
                departure_time=datetime(2026, 4, 15, 10, 0),
                arrival_time=datetime(2026, 4, 15, 15, 0),
                base_price=Decimal('500.00'),
                status=FlightStatus.active
            )
            db.session.add(test_flight)
            db.session.commit()
            flight_id = test_flight.id

            response = client.delete(f'/api/flights/{flight_id}',
                headers=admin_headers)

            assert response.status_code == 200
            data = response.get_json()

            # Check response structure
            assert 'message' in data
            assert str(flight_id) in data['message']
            assert 'deleted successfully' in data['message']


class TestFlightRoutesExceptionHandlers:
    """Test broad exception handlers in flight routes."""

    def test_get_airports_unexpected_exception(self, client, app, auth_headers):
        """Test get_airports handles unexpected exceptions."""
        with app.app_context():
            with patch('ticket_management_system.resources.flights.FlightService.get_available_airports') as mock_service:
                mock_service.side_effect = Exception('Unexpected database error')

                response = client.get('/api/flights/airports', headers=auth_headers)

                assert response.status_code == 500
                data = response.get_json()
                assert 'error' in data
                assert 'Internal Server Error' in data['error']
                assert 'message' in data

    def test_search_flights_unexpected_exception(self, client, app, auth_headers):
        """Test search_flights handles unexpected exceptions."""
        with app.app_context():
            with patch('ticket_management_system.resources.flights.FlightService.search_flights') as mock_service:
                mock_service.side_effect = Exception('Database connection failed')

                response = client.get('/api/flights/search', headers=auth_headers)

                assert response.status_code == 500
                data = response.get_json()
                assert 'error' in data
                assert 'Internal Server Error' in data['error']

    def test_add_flight_unexpected_exception(self, client, app, admin_headers):
        """Test add_flight handles unexpected exceptions."""
        with app.app_context():
            with patch('ticket_management_system.resources.flights.FlightService.create_flight') as mock_service:
                mock_service.side_effect = Exception('Database integrity error')

                response = client.post(
                    '/api/flights/',
                    json={
                        'flight_code': 'AA999',
                        'origin_airport': 'JFK',
                        'destination_airport': 'LAX',
                        'departure_time': '2026-12-25 10:30:00',
                        'arrival_time': '2026-12-25 14:45:00',
                        'base_price': 299.99
                    },
                    headers=admin_headers
                )

                assert response.status_code == 500
                data = response.get_json()
                assert 'error' in data
                assert 'Internal Server Error' in data['error']

    def test_delete_flight_unexpected_exception(self, client, app, admin_headers):
        """Test delete_flight handles unexpected exceptions."""
        with app.app_context():
            import uuid
            flight_id = uuid.uuid4()

            with patch('ticket_management_system.resources.flights.FlightService.delete_flight') as mock_service:
                mock_service.side_effect = Exception('Database delete failed')

                response = client.delete(f'/api/flights/{flight_id}', headers=admin_headers)

                assert response.status_code == 500
                data = response.get_json()
                assert 'error' in data
                assert 'Internal Server Error' in data['error']

    def test_update_flight_unexpected_exception(self, client, app, admin_headers):
        """Test update_flight handles unexpected exceptions."""
        with app.app_context():
            import uuid
            flight_id = uuid.uuid4()

            with patch('ticket_management_system.resources.flights.FlightService.update_flight') as mock_service:
                mock_service.side_effect = Exception('Database update failed')

                response = client.put(
                    f'/api/flights/{flight_id}',
                    json={'base_price': 399.99},
                    headers=admin_headers
                )

                assert response.status_code == 500
                data = response.get_json()
                assert 'error' in data
                assert 'Internal Server Error' in data['error']


