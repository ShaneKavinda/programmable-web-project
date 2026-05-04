"""Business logic for user operations."""
import os
from datetime import datetime, timedelta, timezone
import jwt
from ticket_management_system.extensions import db
from ticket_management_system.models import User
from ticket_management_system.utils import format_pagination_response
from ticket_management_system.exceptions import (
    UserNotFoundError,
    TokenExpiredError,
    InvalidTokenError,
    EmailAlreadyExistsError,
    ResourcePermissionError,
)

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dummy-secret-key-for-development')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_MINUTES = int(os.getenv('JWT_EXPIRATION_MINUTES', '30'))
JWT_EXPIRATION_SECONDS = JWT_EXPIRATION_MINUTES * 60

USER_RESOURCES = (
    'flights:read',
    'bookings:read',
    'bookings:write',
    'payments:create',
    'users:read:self',
    'users:update:self',
)
class UserService:
    """Service class for user operations."""
    @staticmethod
    def email_exists(email):
        """Check if email already exists in database."""
        return User.query.filter_by(email=email).first() is not None

    @staticmethod
    def create_user(firstname, lastname, email):
        """Create a new user identity."""
        new_user = User(
            firstname=firstname,
            lastname=lastname,
            email=email,
        )

        db.session.add(new_user)
        db.session.commit()

        return new_user

    @staticmethod
    def get_permitted_resources(_user):
        """Return the resource scopes allowed for a user."""
        return list(USER_RESOURCES)

    @staticmethod
    def token_expires_in_seconds():
        """Return token lifetime in seconds."""
        return JWT_EXPIRATION_SECONDS

    @staticmethod
    def generate_token(user, permitted_resources=None):
        """Generate a scoped JWT token for a user identity."""
        issued_at = datetime.now(timezone.utc)
        token_payload = {
            'user_id': str(user.id),
            'email': user.email,
            'permitted_resources': list(permitted_resources or UserService.get_permitted_resources(user)),
            'exp': issued_at + timedelta(seconds=JWT_EXPIRATION_SECONDS),
            'iat': issued_at
        }

        token = jwt.encode(token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token

    @staticmethod
    def format_user_response(user, include_token=False):
        """Format user data for API response, optionally including a scoped token."""
        response = {
            'user': {
                'id': str(user.id),
                'firstname': user.firstname,
                'lastname': user.lastname,
                'email': user.email,
                'created_at': user.created_at.isoformat()
            }
        }

        if include_token:
            permitted_resources = UserService.get_permitted_resources(user)
            token = UserService.generate_token(user)
            response['token'] = token
            response['token_type'] = 'Bearer'
            response['expires_in'] = JWT_EXPIRATION_SECONDS
            response['permitted_resources'] = permitted_resources

        return response

    @staticmethod
    def verify_token(token, required_resource=None):
        """Verify a scoped JWT token, return user or raise exception."""
        try:
            import uuid as uuid_lib
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            # Convert string UUID to UUID object for database compatibility
            user_id = payload['user_id']
            if isinstance(user_id, str):
                user_id = uuid_lib.UUID(user_id)

            user = User.query.filter_by(id=user_id).first()

            if not user:
                raise UserNotFoundError()

            if required_resource:
                permitted_resources = payload.get('permitted_resources', [])
                if required_resource not in permitted_resources:
                    raise ResourcePermissionError(required_resource)

            return user

        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError() from exc
        except ResourcePermissionError:
            raise
        except (KeyError, ValueError, jwt.InvalidTokenError) as exc:
            raise InvalidTokenError() from exc

    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID."""
        return User.query.filter_by(id=user_id).first()

    @staticmethod
    def get_paginated_users(page=1, per_page=10):
        """Get paginated list of all users."""
        # Validate pagination parameters
        page = max(page, 1)
        per_page = per_page if per_page > 0 else 10  # Default to 10 if invalid
        per_page = min(per_page, 100)

        # Query users with pagination
        pagination = User.query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        users_data = [UserService.format_user_detail(user) for user in pagination.items]

        return format_pagination_response('users', users_data, pagination)

    @staticmethod
    def format_user_detail(user):
        """Format user details for response."""
        return {
            'user': {
                'id': str(user.id),
                'firstname': user.firstname,
                'lastname': user.lastname,
                'email': user.email,
                'created_at': user.created_at.isoformat(),
                'updated_at': user.updated_at.isoformat()
            }
        }

    @staticmethod
    def update_user_profile(user, firstname=None, lastname=None, email=None):
        """Update user profile."""
        # Validate email uniqueness if provided
        if email and email != user.email:
            if UserService.email_exists(email):
                raise EmailAlreadyExistsError()
            user.email = email

        # Update firstname if provided
        if firstname is not None:
            user.firstname = firstname

        # Update lastname if provided
        if lastname is not None:
            user.lastname = lastname

        user.updated_at = datetime.now(timezone.utc)

        # Save changes
        db.session.commit()
        return user
