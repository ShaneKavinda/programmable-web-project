"""User identity and scoped-token API endpoints."""
import logging
import os
import secrets
from functools import wraps
from flask import Blueprint, request, jsonify, make_response
from marshmallow import ValidationError
from ticket_management_system.utils import handle_validation_error, handle_general_error, handle_conflict_error
from ticket_management_system.resources.user_service import UserService
from ticket_management_system.static.schema.user_schemas import UserProfileUpdateSchema, UserTokenRequestSchema
from ticket_management_system.exceptions import (
    TokenExpiredError,
    InvalidTokenError,
    UserNotFoundError,
    EmailAlreadyExistsError,
    ResourcePermissionError,
)

user_bp = Blueprint('users', __name__, url_prefix='/api/users')
logger = logging.getLogger(__name__)

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "").strip()
if not ADMIN_API_KEY:
    ADMIN_API_KEY = secrets.token_urlsafe(32)
    logger.warning(
        "ADMIN_API_KEY is not set. Generated temporary key for this process: %s",
        ADMIN_API_KEY,
    )


def _attach_refreshed_token(response, user):
    """Attach a refreshed token to successful protected responses."""
    if 200 <= response.status_code < 400:
        response.headers['X-Refreshed-Token'] = UserService.generate_token(user)
        response.headers['X-Token-Expires-In'] = str(UserService.token_expires_in_seconds())
        response.headers['Access-Control-Expose-Headers'] = (
            'X-Refreshed-Token, X-Token-Expires-In'
        )
    return response


def token_required(required_resource=None):
    """Decorator to require a scoped JWT token.

    Supports both @token_required and @token_required('resource:scope').
    """
    if callable(required_resource):
        view_func = required_resource
        required_resource = None
        return token_required(required_resource)(view_func)

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None

            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                try:
                    token_type, token = auth_header.split(" ", 1)
                    if token_type.lower() != 'bearer':
                        raise ValueError
                except ValueError:
                    return jsonify({
                        'error': 'Invalid authorization header format',
                        'message': 'Use format: Bearer <token>'
                    }), 401

            if not token:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'No token provided'
                }), 401

            try:
                token_user = UserService.verify_token(
                    token,
                    required_resource=required_resource
                )
            except TokenExpiredError as e:
                return jsonify({
                    'error': 'Token expired',
                    'message': e.message
                }), 401
            except ResourcePermissionError as e:
                return jsonify({
                    'error': 'Forbidden',
                    'message': e.message
                }), 403
            except (InvalidTokenError, UserNotFoundError) as e:
                return jsonify({
                    'error': 'Invalid token',
                    'message': e.message
                }), 401

            response = make_response(f(token_user, *args, **kwargs))
            return _attach_refreshed_token(response, token_user)

        return decorated

    return decorator


def _issue_token_for_user_id(user_id):
    """Issue a scoped token for an existing user ID."""
    user = UserService.get_user_by_id(user_id)
    if not user:
        raise UserNotFoundError(user_id)

    response = UserService.format_user_response(user, include_token=True)
    response['message'] = 'Token issued successfully'
    return response

@user_bp.route('/token', methods=['POST'])
def issue_token():  # pylint: disable=too-many-return-statements
    """Issue a scoped token for a user ID."""
    try:
        try:
            json_data = request.get_json()
        except Exception:  # pylint: disable=broad-exception-caught
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request body must be valid JSON'
            }), 400

        if json_data is None:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request body must be JSON'
            }), 400

        schema = UserTokenRequestSchema()
        validated_data = schema.load(json_data)

        return jsonify(_issue_token_for_user_id(validated_data['user_id'])), 200

    except ValidationError as err:
        return handle_validation_error(err)
    except UserNotFoundError as e:
        return jsonify({
            'error': 'Not Found',
            'message': e.message
        }), 404
    except Exception as e:  # pylint: disable=broad-exception-caught
        return handle_general_error(e, rollback=False)


@user_bp.route('/<uuid:user_id>/token', methods=['GET'])
def issue_token_by_user_id(user_id):
    """Issue a scoped token when the user ID is passed in the URL."""
    try:
        return jsonify(_issue_token_for_user_id(user_id)), 200
    except UserNotFoundError as e:
        return jsonify({
            'error': 'Not Found',
            'message': e.message
        }), 404
    except Exception as e:  # pylint: disable=broad-exception-caught
        return handle_general_error(e, rollback=False)


def legacy_auth_removed():
    """Return the standard response for removed password auth endpoints."""
    return jsonify({
        'error': 'Gone',
        'message': 'Password login/register has been removed. Request a scoped token with /api/users/token.'
    }), 410


@user_bp.route('/register', methods=['POST'])
def register_removed():
    """Password registration is no longer part of authentication."""
    return legacy_auth_removed()


@user_bp.route('/login', methods=['POST'])
def login_removed():
    """Password login is no longer part of authentication."""
    return legacy_auth_removed()


def admin_required(f):
    """Decorator to require admin API key via x-api-key header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("x-api-key", "").strip()
        if not api_key:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Missing x-api-key header'
            }), 401
        if api_key != ADMIN_API_KEY:
            return jsonify({
                'error': 'Forbidden',
                'message': 'Invalid API key'
            }), 403

        return f(*args, **kwargs)

    return decorated


@user_bp.route('/me', methods=['GET'])
@token_required('users:read:self')
def get_token_user(token_user):
    """Get token user profile."""
    response = UserService.format_user_detail(token_user)
    return jsonify(response), 200


@user_bp.route('/me', methods=['PATCH'])
@token_required('users:update:self')
def update_token_user(token_user):  # pylint: disable=too-many-return-statements
    """Update token user profile."""
    try:
        # Get JSON data - handle empty body
        try:
            json_data = request.get_json()
        except Exception:  # pylint: disable=broad-exception-caught
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request body must be valid JSON'
            }), 400

        # Check if request body is empty or None
        if json_data is None:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request body must be JSON'
            }), 400

        # Validate request data using Marshmallow schema
        schema = UserProfileUpdateSchema()
        validated_data = schema.load(json_data)

        # At least one field must be provided
        if not validated_data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'At least one field (firstname, lastname, or email) must be provided'
            }), 400

        # Update user profile
        updated_user = UserService.update_user_profile(
            user=token_user,
            firstname=validated_data.get('firstname'),
            lastname=validated_data.get('lastname'),
            email=validated_data.get('email')
        )

        # Format response
        response = UserService.format_user_detail(updated_user)
        response['message'] = 'Profile updated successfully'

        return jsonify(response), 200

    except ValidationError as err:
        return handle_validation_error(err)
    except EmailAlreadyExistsError as e:
        return handle_conflict_error(e.message)
    except Exception as e:  # pylint: disable=broad-exception-caught
        return handle_general_error(e)


@user_bp.route('/', methods=['GET'])
@admin_required
def get_all_users():
    """Get paginated list of all users (admin only)."""
    # Get pagination parameters from query string
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    result = UserService.get_paginated_users(page, per_page)

    return jsonify(result), 200
