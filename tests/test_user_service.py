"""Unit tests for UserService class."""

from datetime import datetime, timedelta, timezone
import os
import jwt
import pytest
from ticket_management_system.extensions import db
from ticket_management_system.resources.user_service import UserService
from ticket_management_system.exceptions import (
    InvalidTokenError,
    ResourcePermissionError,
    TokenExpiredError,
    UserNotFoundError,
)


class TestUserServiceDatabaseOperations:
    def test_email_exists_true(self, app, test_user):
        with app.app_context():
            assert UserService.email_exists(test_user.email) is True

    def test_email_exists_false(self, app):
        with app.app_context():
            assert UserService.email_exists("nonexistent@example.com") is False

    def test_create_user(self, app):
        with app.app_context():
            user = UserService.create_user(
                firstname="Jane",
                lastname="Smith",
                email="jane@example.com",
            )
            assert user.id is not None
            assert user.email == "jane@example.com"
            db.session.delete(user)
            db.session.commit()


class TestUserServiceTokenAuthentication:
    def test_generate_token(self, app, test_user):
        with app.app_context():
            token = UserService.generate_token(test_user)
            secret = os.getenv("JWT_SECRET_KEY", "dummy-secret-key-for-development")
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            assert payload["user_id"] == str(test_user.id)
            assert payload["email"] == test_user.email
            assert "role" not in payload
            assert "users:read:self" in payload["permitted_resources"]

    def test_verify_token_valid(self, app, test_user):
        with app.app_context():
            token = UserService.generate_token(test_user)
            user = UserService.verify_token(token)
            assert user.id == test_user.id

    def test_verify_token_with_required_resource(self, app, test_user):
        with app.app_context():
            token = UserService.generate_token(test_user)
            user = UserService.verify_token(token, required_resource="users:read:self")
            assert user.id == test_user.id

    def test_verify_token_rejects_unpermitted_resource(self, app, test_user):
        with app.app_context():
            token = UserService.generate_token(test_user)
            with pytest.raises(ResourcePermissionError):
                UserService.verify_token(token, required_resource="users:read:all")

    def test_verify_token_expired(self, app, test_user):
        with app.app_context():
            secret = os.getenv("JWT_SECRET_KEY", "dummy-secret-key-for-development")
            payload = {
                "user_id": str(test_user.id),
                "email": test_user.email,
                "permitted_resources": UserService.get_permitted_resources(test_user),
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
                "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            }
            token = jwt.encode(payload, secret, algorithm="HS256")
            with pytest.raises(TokenExpiredError):
                UserService.verify_token(token)

    def test_verify_token_invalid(self, app):
        with app.app_context():
            with pytest.raises(InvalidTokenError):
                UserService.verify_token("invalid.token.here")

    def test_verify_token_user_not_found(self, app):
        with app.app_context():
            import uuid

            fake_id = str(uuid.uuid4())
            secret = os.getenv("JWT_SECRET_KEY", "dummy-secret-key-for-development")
            payload = {
                "user_id": fake_id,
                "email": "fake@example.com",
                "permitted_resources": ["users:read:self"],
                "exp": datetime.now(timezone.utc) + timedelta(hours=24),
                "iat": datetime.now(timezone.utc),
            }
            token = jwt.encode(payload, secret, algorithm="HS256")
            with pytest.raises(UserNotFoundError):
                UserService.verify_token(token)


class TestUserServiceFormatting:
    def test_format_user_response_without_token(self, app, test_user):
        with app.app_context():
            response = UserService.format_user_response(test_user, include_token=False)
            assert response["user"]["id"] == str(test_user.id)
            assert "role" not in response["user"]
            assert "token" not in response

    def test_format_user_response_with_token(self, app, test_user):
        with app.app_context():
            response = UserService.format_user_response(test_user, include_token=True)
            assert response["token_type"] == "Bearer"
            assert response["expires_in"] == UserService.token_expires_in_seconds()
            assert "permitted_resources" in response

    def test_format_user_detail(self, app, test_user):
        with app.app_context():
            response = UserService.format_user_detail(test_user)
            assert response["user"]["id"] == str(test_user.id)
            assert "role" not in response["user"]


class TestUserServicePagination:
    def test_get_paginated_users_default(self, app, multiple_users):
        with app.app_context():
            result = UserService.get_paginated_users()
            assert "users" in result and "pagination" in result
            assert result["pagination"]["page"] == 1

    def test_get_paginated_users_custom_page_size(self, app, multiple_users):
        with app.app_context():
            result = UserService.get_paginated_users(page=1, per_page=3)
            assert len(result["users"]) <= 3
            assert result["pagination"]["per_page"] == 3
