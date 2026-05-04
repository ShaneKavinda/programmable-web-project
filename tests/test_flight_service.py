"""
Unit tests for FlightService class.
Tests all business logic methods in the flight service layer.
"""

from datetime import datetime, timedelta
from ticket_management_system.extensions import db
from decimal import Decimal
from ticket_management_system.models import Flight, FlightStatus
from ticket_management_system.resources.flight_service import FlightService


class TestFlightServiceAirports:
    """Test get_available_airports method."""

    def test_get_available_airports_empty_database(self, app):
        """Test getting airports when no flights exist."""
        with app.app_context():
            # Clean up all flights first
            Flight.query.delete()
            db.session.commit()

            result = FlightService.get_available_airports()

            assert 'airports' in result
            assert 'count' in result
            assert result['count'] == 0
            assert result['airports'] == []

    def test_get_available_airports_with_flights(self, app, sample_flights):
        """Test getting airports with flights in database."""
        result = FlightService.get_available_airports()

        assert result['count'] > 0
        assert isinstance(result['airports'], list)
        assert len(result['airports']) == result['count']

    def test_get_available_airports_distinct(self, app):
        """Test that airports are unique (no duplicates)."""
        with app.app_context():
            # Create flights with same airports
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

            result = FlightService.get_available_airports()

            # Should only have 2 unique airports (JFK and LAX)
            assert result['count'] == 2
            assert 'JFK' in result['airports']
            assert 'LAX' in result['airports']

            # Cleanup
            db.session.delete(flight1)
            db.session.delete(flight2)
            db.session.commit()

    def test_get_available_airports_sorted(self, app):
        """Test that airports are sorted alphabetically."""
        with app.app_context():
            # Create flights with different airports
            flight1 = Flight(
                flight_code='AA101',
                origin_airport='ORD',
                destination_airport='ATL',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('199.99'),
                status=FlightStatus.active
            )
            flight2 = Flight(
                flight_code='AA102',
                origin_airport='LAX',
                destination_airport='JFK',
                departure_time=datetime(2026, 3, 16, 10, 0),
                arrival_time=datetime(2026, 3, 16, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight1)
            db.session.add(flight2)
            db.session.commit()

            result = FlightService.get_available_airports()

            # Check if sorted (ATL, JFK, LAX, ORD)
            assert result['airports'] == sorted(result['airports'])

            # Cleanup
            db.session.delete(flight1)
            db.session.delete(flight2)
            db.session.commit()

    def test_get_available_airports_origin_and_destination(self, app):
        """Test that both origin and destination airports are included."""
        with app.app_context():
            flight = Flight(
                flight_code='AA101',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            result = FlightService.get_available_airports()

            assert 'JFK' in result['airports']
            assert 'LAX' in result['airports']

            # Cleanup
            db.session.delete(flight)
            db.session.commit()


class TestFlightServiceSearch:
    """Test search_flights method."""

    def test_search_flights_no_filters(self, app, sample_flights):
        """Test searching without any filters returns all active flights."""
        result = FlightService.search_flights()

        assert 'flights' in result
        assert 'pagination' in result
        assert isinstance(result['flights'], list)
        assert result['pagination']['page'] == 1
        assert result['pagination']['per_page'] == 10

    def test_search_flights_by_origin(self, app, sample_flights):
        """Test searching by origin airport."""
        result = FlightService.search_flights(origin_airport='JFK')

        assert len(result['flights']) > 0
        for flight in result['flights']:
            assert 'JFK' in flight['origin_airport'].upper()

    def test_search_flights_by_destination(self, app, sample_flights):
        """Test searching by destination airport."""
        result = FlightService.search_flights(destination_airport='LAX')

        assert len(result['flights']) > 0
        for flight in result['flights']:
            assert 'LAX' in flight['destination_airport'].upper()

    def test_search_flights_by_origin_and_destination(self, app):
        """Test searching by both origin and destination."""
        with app.app_context():
            # Create specific flights
            flight = Flight(
                flight_code='AA101',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            result = FlightService.search_flights(
                origin_airport='JFK',
                destination_airport='LAX'
            )

            assert len(result['flights']) > 0
            for f in result['flights']:
                assert 'JFK' in f['origin_airport']
                assert 'LAX' in f['destination_airport']

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_search_flights_by_departure_date(self, app):
        """Test searching by departure date."""
        with app.app_context():
            target_date = datetime(2026, 3, 15, 10, 0)
            flight = Flight(
                flight_code='AA101',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=target_date,
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            result = FlightService.search_flights(departure_date='2026-03-15')

            assert len(result['flights']) > 0
            for f in result['flights']:
                flight_date = datetime.fromisoformat(f['departure_time']).date()
                assert flight_date == target_date.date()

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_search_flights_by_arrival_date(self, app):
        """Test searching by arrival date."""
        with app.app_context():
            target_date = datetime(2026, 3, 15, 14, 0)
            flight = Flight(
                flight_code='AA101',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=target_date,
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            result = FlightService.search_flights(arrival_date='2026-03-15')

            assert len(result['flights']) > 0

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_search_flights_invalid_date_format(self, app, sample_flights):
        """Test that invalid date format doesn't crash, just ignores filter."""
        result = FlightService.search_flights(departure_date='invalid-date')

        # Should still return results, just ignore the invalid filter
        assert 'flights' in result
        assert isinstance(result['flights'], list)

    def test_search_flights_invalid_arrival_date_format(self, app, sample_flights):
        """Invalid arrival_date is ignored (except branch coverage)."""
        result = FlightService.search_flights(arrival_date='not-a-date')
        assert 'flights' in result
        assert isinstance(result['flights'], list)

    def test_search_flights_status_filter_non_all(self, app):
        """status='inactive' follows non-all status branch."""
        with app.app_context():
            inactive = Flight(
                flight_code='AA199',
                origin_airport='HEL',
                destination_airport='ARN',
                departure_time=datetime(2026, 7, 1, 9, 0),
                arrival_time=datetime(2026, 7, 1, 10, 0),
                base_price=Decimal('99.99'),
                status=FlightStatus.inactive,
            )
            active = Flight(
                flight_code='AA198',
                origin_airport='HEL',
                destination_airport='ARN',
                departure_time=datetime(2026, 7, 1, 11, 0),
                arrival_time=datetime(2026, 7, 1, 12, 0),
                base_price=Decimal('109.99'),
                status=FlightStatus.active,
            )
            db.session.add(inactive)
            db.session.add(active)
            db.session.commit()
            result = FlightService.search_flights(status="inactive")
            assert all(f["status"] == "inactive" for f in result["flights"])
            db.session.delete(inactive)
            db.session.delete(active)
            db.session.commit()

    def test_search_flights_case_insensitive(self, app):
        """Test that airport search is case-insensitive."""
        with app.app_context():
            flight = Flight(
                flight_code='AA101',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            result_lower = FlightService.search_flights(origin_airport='jfk')
            result_upper = FlightService.search_flights(origin_airport='JFK')
            result_mixed = FlightService.search_flights(origin_airport='Jfk')

            assert len(result_lower['flights']) > 0
            assert len(result_upper['flights']) > 0
            assert len(result_mixed['flights']) > 0

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_search_flights_partial_match(self, app):
        """Test that airport search supports partial matching."""
        with app.app_context():
            flight = Flight(
                flight_code='AA101',
                origin_airport='JFK - John F Kennedy International',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            # Should match with just 'JFK' or 'Kennedy'
            result1 = FlightService.search_flights(origin_airport='JFK')
            result2 = FlightService.search_flights(origin_airport='Kennedy')

            assert len(result1['flights']) > 0
            assert len(result2['flights']) > 0

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_search_flights_only_active(self, app):
        """Test that only active flights are returned."""
        with app.app_context():
            active_flight = Flight(
                flight_code='AA101',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            cancelled_flight = Flight(
                flight_code='AA102',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 16, 10, 0),
                arrival_time=datetime(2026, 3, 16, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.cancelled
            )
            db.session.add(active_flight)
            db.session.add(cancelled_flight)
            db.session.commit()

            result = FlightService.search_flights()

            # Should only have active flights
            for flight in result['flights']:
                assert flight['status'] == 'active'

            # Cleanup
            db.session.delete(active_flight)
            db.session.delete(cancelled_flight)
            db.session.commit()

    def test_search_flights_ordered_by_departure(self, app):
        """Test that results are ordered by departure time."""
        with app.app_context():
            flight1 = Flight(
                flight_code='AA101',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 14, 0),
                arrival_time=datetime(2026, 3, 15, 18, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            flight2 = Flight(
                flight_code='AA102',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight1)
            db.session.add(flight2)
            db.session.commit()

            result = FlightService.search_flights()

            # First flight should have earlier departure
            if len(result['flights']) >= 2:
                first_departure = datetime.fromisoformat(result['flights'][0]['departure_time'])
                second_departure = datetime.fromisoformat(result['flights'][1]['departure_time'])
                assert first_departure <= second_departure

            # Cleanup
            db.session.delete(flight1)
            db.session.delete(flight2)
            db.session.commit()


class TestFlightServicePagination:
    """Test pagination in search_flights method."""

    def test_search_flights_default_pagination(self, app, sample_flights):
        """Test default pagination parameters."""
        result = FlightService.search_flights()

        assert result['pagination']['page'] == 1
        assert result['pagination']['per_page'] == 10
        assert len(result['flights']) <= 10

    def test_search_flights_custom_page_size(self, app, sample_flights):
        """Test custom page size."""
        result = FlightService.search_flights(page=1, per_page=5)

        assert result['pagination']['per_page'] == 5
        assert len(result['flights']) <= 5

    def test_search_flights_second_page(self, app, multiple_flights):
        """Test getting second page of results."""
        result = FlightService.search_flights(page=2, per_page=3)

        assert result['pagination']['page'] == 2
        assert result['pagination']['has_prev'] is True

    def test_search_flights_invalid_page_defaults_to_one(self, app, sample_flights):
        """Test that invalid page number defaults to 1."""
        result = FlightService.search_flights(page=-1)

        assert result['pagination']['page'] == 1

    def test_search_flights_invalid_per_page_defaults(self, app, sample_flights):
        """Test that invalid per_page defaults to 1 (minimum)."""
        result = FlightService.search_flights(per_page=-5)

        assert result['pagination']['per_page'] == 1

    def test_search_flights_max_per_page_cap(self, app, sample_flights):
        """Test that per_page is capped at 100."""
        result = FlightService.search_flights(per_page=200)

        assert result['pagination']['per_page'] == 100

    def test_search_flights_sort_by_price_desc(self, app, multiple_flights):
        """Highest base_price first when sorting price descending."""
        result = FlightService.search_flights(sort_by='base_price', sort_order='desc', per_page=1)
        assert result['flights'][0]['flight_code'] == 'FL109'

    def test_search_flights_pagination_metadata(self, app, multiple_flights):
        """Test pagination metadata is correct."""
        result = FlightService.search_flights(page=1, per_page=3)

        pagination = result['pagination']
        assert 'total_pages' in pagination
        assert 'total_items' in pagination
        assert 'has_next' in pagination
        assert 'has_prev' in pagination
        assert 'next_page' in pagination
        assert 'prev_page' in pagination

        assert pagination['has_prev'] is False
        assert pagination['prev_page'] is None


class TestFlightServiceHelpers:
    """Test helper methods."""

    def test_get_flight_by_id(self, app):
        """Test getting flight by ID."""
        with app.app_context():
            flight = Flight(
                flight_code='AA101',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            result = FlightService.get_flight_by_id(flight.id)

            assert result is not None
            assert result.id == flight.id
            assert result.flight_code == 'AA101'

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_get_flight_by_id_not_found(self, app):
        """Test getting flight with non-existent ID."""
        with app.app_context():
            import uuid
            fake_id = uuid.uuid4()
            result = FlightService.get_flight_by_id(fake_id)

            assert result is None

    def test_format_flight_detail(self, app):
        """Test formatting flight detail."""
        with app.app_context():
            # Clean up first
            Flight.query.filter_by(flight_code='TEST_FORMAT').delete(synchronize_session=False)
            db.session.commit()

            flight = Flight(
                flight_code='TEST_FORMAT',
                origin_airport='JFK',
                destination_airport='LAX',
                departure_time=datetime(2026, 3, 15, 10, 0),
                arrival_time=datetime(2026, 3, 15, 14, 0),
                base_price=Decimal('299.99'),
                status=FlightStatus.active
            )
            db.session.add(flight)
            db.session.commit()

            result = FlightService.format_flight_detail(flight)

            assert 'id' in result
            assert result['id'] == str(flight.id)
            assert result['flight_code'] == 'TEST_FORMAT'
            assert result['origin_airport'] == 'JFK'
            assert result['destination_airport'] == 'LAX'
            assert 'departure_time' in result
            assert 'arrival_time' in result
            assert result['base_price'] == '299.99'
            assert result['status'] == 'active'
            assert 'created_at' in result
            assert 'updated_at' in result

            # Cleanup
            db.session.delete(flight)
            db.session.commit()

    def test_update_flight_status_string_and_enum_paths(self, app):
        """update_flight supports status as str and FlightStatus enum."""
        with app.app_context():
            flight = Flight(
                flight_code='AA177',
                origin_airport='HEL',
                destination_airport='RIX',
                departure_time=datetime(2026, 8, 1, 10, 0),
                arrival_time=datetime(2026, 8, 1, 11, 0),
                base_price=Decimal('111.00'),
                status=FlightStatus.active,
            )
            db.session.add(flight)
            db.session.commit()
            updated = FlightService.update_flight(flight.id, status="delayed")
            assert updated.status == FlightStatus.delayed
            updated = FlightService.update_flight(flight.id, status=FlightStatus.landed)
            assert updated.status == FlightStatus.landed
            db.session.delete(flight)
            db.session.commit()


class TestFlightServiceResponseFormat:
    """Test response formatting."""

    def test_search_response_structure(self, app, sample_flights):
        """Test that search response has correct structure."""
        result = FlightService.search_flights()

        # Check top-level keys
        assert 'flights' in result
        assert 'pagination' in result

        # Check flight structure
        if result['flights']:
            flight = result['flights'][0]
            assert 'id' in flight
            assert 'flight_code' in flight
            assert 'origin_airport' in flight
            assert 'destination_airport' in flight
            assert 'departure_time' in flight
            assert 'arrival_time' in flight
            assert 'base_price' in flight
            assert 'status' in flight
            assert 'created_at' in flight

        # Check pagination structure
        pagination = result['pagination']
        assert 'page' in pagination
        assert 'per_page' in pagination
        assert 'total_pages' in pagination
        assert 'total_items' in pagination
        assert 'has_next' in pagination
        assert 'has_prev' in pagination
        assert 'next_page' in pagination
        assert 'prev_page' in pagination
