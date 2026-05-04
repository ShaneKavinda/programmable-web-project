"""Validation schemas for booking endpoints."""
from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class PassengerSchema(Schema):
    """Schema for passenger validation."""
    passenger_name = fields.Str(required=False, validate=validate.Length(min=1, max=101))
    passenger_fname = fields.Str(required=False, validate=validate.Length(min=1, max=50))
    passenger_lname = fields.Str(required=False, validate=validate.Length(min=1, max=50))
    email = fields.Email(
        required=False,
        allow_none=False,
        validate=validate.Length(max=255, error='email must be 255 characters or less')
    )
    passenger_passport_num = fields.Str(required=True, validate=validate.Length(min=1, max=12))
    seat_num = fields.Str(required=True, validate=validate.Length(min=1, max=4))
    seat_class = fields.Str(
        required=False,
        load_default="economy",
        validate=validate.OneOf(["economy", "business", "first"]),
    )

    @validates_schema
    def validate_passenger_name(self, data, **_kwargs):
        """Require either split passenger names or a legacy full passenger name."""
        has_legacy_name = bool(data.get("passenger_name"))
        has_first_name = bool(data.get("passenger_fname"))
        has_last_name = bool(data.get("passenger_lname"))

        if has_first_name and has_last_name:
            return
        if has_legacy_name and not (has_first_name or has_last_name):
            return

        raise ValidationError({
            "passenger_fname": ["passenger_fname and passenger_lname are required together."],
            "passenger_lname": ["passenger_fname and passenger_lname are required together."]
        })


class BookTicketsSchema(Schema):
    """Schema for booking tickets validation."""
    user_id = fields.UUID(required=False, allow_none=True, load_default=None)
    flight_id = fields.UUID(required=True)
    booking_status = fields.Str(
        required=False,
        load_default="booked",
        validate=validate.OneOf(["booked", "paid", "cancelled", "refunded"]),
    )
    passengers = fields.List(
        fields.Nested(PassengerSchema),
        required=True,
        validate=validate.Length(min=1, max=10),
    )

    @validates_schema
    def validate_first_passenger_email(self, data, **_kwargs):
        """Require owner/receipt email on the first passenger."""
        passengers = data.get("passengers") or []
        if not passengers:
            return

        first_email = passengers[0].get("email")
        if not first_email:
            raise ValidationError({
                "passengers": {
                    0: {
                        "email": ["First passenger email is required for booking ownership."]
                    }
                }
            })


class PaginationQuerySchema(Schema):
    """Schema for pagination query parameters."""
    page = fields.Int(required=False, load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(required=False, load_default=10, validate=validate.Range(min=1, max=100))
    all = fields.Bool(required=False, load_default=False)


class SeatAvailabilityQuerySchema(Schema):
    """Schema for seat availability check."""
    flight_id = fields.UUID(required=True)
    seat_num = fields.Str(required=True, validate=validate.Length(min=1, max=4))


class UpdateBookingSchema(Schema):
    """Schema for updating booking status."""
    booking_status = fields.Str(
        required=True,
        validate=validate.OneOf(["booked", "paid", "cancelled", "refunded"]),
    )
