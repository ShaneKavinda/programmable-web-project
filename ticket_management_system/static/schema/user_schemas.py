"""Validation schemas for user endpoints."""

from marshmallow import Schema, fields, validates, ValidationError, validate


class UserProfileUpdateSchema(Schema):
    """Schema for user profile update validation."""

    firstname = fields.Str(
        required=False,
        allow_none=False,
        validate=validate.Length(
            min=1,
            max=30,
            error="firstname must be between 1 and 30 characters"
        )
    )

    lastname = fields.Str(
        required=False,
        allow_none=False,
        validate=validate.Length(
            min=1,
            max=30,
            error="lastname must be between 1 and 30 characters"
        )
    )

    email = fields.Email(
        required=False,
        allow_none=False,
        validate=validate.Length(
            max=255,
            error="email must be 255 characters or less"
        )
    )

    @validates("firstname")
    def validate_firstname_not_empty(self, value, **_kwargs):
        """Validate firstname is not empty or whitespace only."""
        if not value.strip():
            raise ValidationError("firstname cannot be empty or only whitespace")

    @validates("lastname")
    def validate_lastname_not_empty(self, value, **_kwargs):
        """Validate lastname is not empty or whitespace only."""
        if not value.strip():
            raise ValidationError("lastname cannot be empty or only whitespace")


class UserTokenRequestSchema(Schema):
    """Schema for requesting a scoped token by user_id."""

    user_id = fields.UUID(
        required=True,
        error_messages={
            "required": "user_id is required",
            "invalid_uuid": "user_id must be a valid UUID"
        }
    )