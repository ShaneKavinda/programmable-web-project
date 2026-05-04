"""Flight management API endpoints."""
from flask import Blueprint, request, jsonify
from marshmallow import ValidationError
from ticket_management_system.extensions import cache
from ticket_management_system.utils import handle_validation_error, handle_general_error, handle_conflict_error
from ticket_management_system.resources.users import admin_required
from ticket_management_system.static.schema.flight_schemas import FlightSearchSchema, AddFlightSchema, UpdateFlightSchema
from ticket_management_system.resources.flight_service import FlightService
from ticket_management_system.exceptions import FlightAlreadyExistsError, FlightNotFoundError

flight_bp = Blueprint('flights', __name__, url_prefix='/api/flights')


@flight_bp.route('/airports', methods=['GET'])
@cache.cached(timeout=50)
def get_airports():
    """Get list of available airports."""
    try:
        result = FlightService.get_available_airports()
        return jsonify(result), 200
    except Exception as e:  # pylint: disable=broad-exception-caught
        return handle_general_error(e, rollback=False)


@flight_bp.route('/search', methods=['GET'])
def search_flights():
    """Search flights with filters."""
    try:
        # Validate query parameters using Marshmallow schema
        schema = FlightSearchSchema()
        validated_data = schema.load(request.args)

        # Extract validated parameters
        status = validated_data.get('status')
        origin_airport = validated_data.get('origin_airport')
        destination_airport = validated_data.get('destination_airport')
        departure_date = validated_data.get('departure_date')
        arrival_date = validated_data.get('arrival_date')
        page = validated_data.get('page', 1)
        per_page = validated_data.get('per_page', 10)
        sort_by = validated_data.get('sort_by', 'departure_time')
        sort_order = validated_data.get('sort_order', 'asc')

        # Convert date objects to strings for service layer
        departure_date_str = departure_date.strftime('%Y-%m-%d') if departure_date else None
        arrival_date_str = arrival_date.strftime('%Y-%m-%d') if arrival_date else None

        # Search flights using service
        result = FlightService.search_flights(
            status=status,
            origin_airport=origin_airport,
            destination_airport=destination_airport,
            departure_date=departure_date_str,
            arrival_date=arrival_date_str,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return jsonify(result), 200
    except ValidationError as err:
        return handle_validation_error(err)
    except Exception as e:  # pylint: disable=broad-exception-caught
        return handle_general_error(e, rollback=False)


@flight_bp.route('/', methods=['POST'])
@admin_required
def add_flight():
    """Add a new flight (admin only)."""
    try:
        # Get and validate request body using Marshmallow schema
        schema = AddFlightSchema()
        validated_data = schema.load(request.get_json())

        # Create flight using service
        new_flight = FlightService.create_flight(
            flight_code=validated_data['flight_code'],
            origin_airport=validated_data['origin_airport'],
            destination_airport=validated_data['destination_airport'],
            departure_time=validated_data['departure_time'],
            arrival_time=validated_data['arrival_time'],
            base_price=validated_data['base_price']
        )

        # Format response
        flight_data = FlightService.format_flight_detail(new_flight)
        response = {
            'flight': flight_data,
            'message': 'Flight created successfully'
        }

        return jsonify(response), 201
    except ValidationError as err:
        return handle_validation_error(err)
    except FlightAlreadyExistsError as err:
        return handle_conflict_error(err.message)
    except Exception as e:  # pylint: disable=broad-exception-caught
        return handle_general_error(e)


@flight_bp.route('/<uuid:flight_id>', methods=['GET'])
def get_flight(flight_id):
    """Get a single flight by ID. Optional include_bookings=1 adds booking id/user/status."""
    try:
        include_bookings = str(request.args.get("include_bookings", "")).lower() in (
            "1",
            "true",
            "yes",
        )
        flight = FlightService.get_flight_by_id(flight_id, load_bookings=include_bookings)
        if not flight:
            raise FlightNotFoundError(flight_id)
        return (
            jsonify(
                {
                    "flight": FlightService.format_flight_detail(
                        flight, include_bookings=include_bookings
                    )
                }
            ),
            200,
        )
    except FlightNotFoundError as err:
        return jsonify({
            'error': 'Not Found',
            'message': err.message
        }), 404
    except Exception as e:  # pylint: disable=broad-exception-caught
        return handle_general_error(e, rollback=False)


@flight_bp.route('/<uuid:flight_id>', methods=['DELETE'])
@admin_required
def delete_flight(flight_id):
    """Delete a flight by ID."""
    try:
        # Delete flight using service
        FlightService.delete_flight(flight_id)
        return jsonify({
            'message': f'Flight {flight_id} deleted successfully'
        }), 200
    except FlightNotFoundError as err:
        return jsonify({
            'error': 'Not Found',
            'message': err.message
        }), 404
    except Exception as e:  # pylint: disable=broad-exception-caught
        return handle_general_error(e)


@flight_bp.route('/<uuid:flight_id>', methods=['PUT'])
@admin_required
def update_flight(flight_id):
    """Update a flight by ID (admin only)."""
    try:
        # Get and validate request body using Marshmallow schema
        schema = UpdateFlightSchema()
        validated_data = schema.load(request.get_json())

        # Update flight using service
        updated_flight = FlightService.update_flight(
            flight_id,
            **validated_data
        )

        # Format response
        flight_data = FlightService.format_flight_detail(updated_flight)
        response = {
            'flight': flight_data,
            'message': 'Flight updated successfully'
        }

        return jsonify(response), 200
    except ValidationError as err:
        return handle_validation_error(err)
    except FlightNotFoundError as err:
        return jsonify({
            'error': 'Not Found',
            'message': err.message
        }), 404
    except Exception as e:  # pylint: disable=broad-exception-caught
        return handle_general_error(e)

