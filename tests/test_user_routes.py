"""
Unit tests for user routes endpoints.
Tests all HTTP endpoints in the user routes blueprint.
"""

import importlib

from ticket_management_system.extensions import db


class TestTokenEndpoint:
    """Test user-ID token grant endpoints."""

    def test_issue_token_by_user_id_success(self, client, app, test_user):
        """A user ID in the URL should also issue a scoped token."""
        with app.app_context():
            response = client.get(f'/api/users/{test_user.id}/token')

            assert response.status_code == 200
            data = response.get_json()
            assert data['user']['id'] == str(test_user.id)
            assert 'token' in data

    def test_issue_token_by_user_id_not_found(self, client):
        """Unknown user id in path returns Not Found."""
        response = client.get('/api/users/00000000-0000-0000-0000-000000000000/token')
        assert response.status_code == 404
        assert response.get_json()['error'] == 'Not Found'

    def test_issue_token_by_user_id_unexpected_exception(self, client, monkeypatch):
        """Generic exception path in issue_token_by_user_id returns handled 500."""
        monkeypatch.setattr(
            "ticket_management_system.resources.users._issue_token_for_user_id",
            lambda *_a, **_k: (_ for _ in ()).throw(Exception("boom")),
        )
        response = client.get('/api/users/00000000-0000-0000-0000-000000000000/token')
        assert response.status_code == 500

    def test_post_issue_token_endpoint_not_found(self, client):
        """POST /api/users/token was removed; callers must use GET /api/users/{user_id}/token."""
        response = client.post('/api/users/token', json={'user_id': '00000000-0000-0000-0000-000000000000'})
        assert response.status_code == 404

    def test_register_endpoint_not_found(self, client):
        """Password registration endpoint does not exist."""
        response = client.post('/api/users/register', json={})

        assert response.status_code == 404

    def test_login_endpoint_not_found(self, client):
        """Password login endpoint does not exist."""
        response = client.post('/api/users/login', json={})

        assert response.status_code == 404

    def test_module_generates_admin_api_key_when_env_missing(self, monkeypatch):
        """Reloading users module without ADMIN_API_KEY exercises fallback generation."""
        monkeypatch.delenv("ADMIN_API_KEY", raising=False)
        users_module = importlib.import_module("ticket_management_system.resources.users")
        reloaded = importlib.reload(users_module)
        try:
            assert isinstance(reloaded.ADMIN_API_KEY, str)
            assert len(reloaded.ADMIN_API_KEY) > 20
        finally:
            monkeypatch.setenv("ADMIN_API_KEY", "test-admin-api-key")
            importlib.reload(reloaded)


class TestGetCurrentUserEndpoint:
    """Test GET /api/users/me endpoint."""

    def test_get_current_user_success(self, client, app, auth_headers):
        """Test getting current user profile with valid token."""
        with app.app_context():
            response = client.get('/api/users/me', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert 'user' in data
            assert 'id' in data['user']
            assert 'firstname' in data['user']
            assert 'lastname' in data['user']
            assert 'email' in data['user']
            assert 'created_at' in data['user']
            assert 'updated_at' in data['user']

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token."""
        response = client.get('/api/users/me')

        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Authentication required'
        assert 'No token provided' in data['message']

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        headers = {'Authorization': 'Bearer invalid.token.here'}
        response = client.get('/api/users/me', headers=headers)

        assert response.status_code == 401
        data = response.get_json()
        assert 'Invalid token' in data['error'] or 'Token expired' in data['error']

    def test_get_current_user_malformed_header(self, client):
        """Test getting current user with malformed Authorization header."""
        headers = {'Authorization': 'InvalidFormat'}
        response = client.get('/api/users/me', headers=headers)

        assert response.status_code == 401
        data = response.get_json()
        assert 'Invalid authorization header format' in data['error']

    def test_get_current_user_non_bearer_token_type(self, client):
        """token_required branch: token type must be Bearer."""
        response = client.get('/api/users/me', headers={'Authorization': 'Basic abc'})
        assert response.status_code == 401
        assert 'Invalid authorization header format' in response.get_json()['error']

    def test_get_current_user_forbidden_by_resource_scope(self, client, monkeypatch):
        """token_required ResourcePermissionError branch returns 403."""
        from ticket_management_system.exceptions import ResourcePermissionError

        monkeypatch.setattr(
            "ticket_management_system.resources.users.UserService.verify_token",
            lambda *_a, **_k: (_ for _ in ()).throw(ResourcePermissionError("users:read:self")),
        )
        response = client.get('/api/users/me', headers={'Authorization': 'Bearer token'})
        assert response.status_code == 403
        assert response.get_json()['error'] == 'Forbidden'

    def test_get_current_user_expired_token(self, client, app, expired_token):
        """Test getting current user with expired token."""
        with app.app_context():
            headers = {'Authorization': f'Bearer {expired_token}'}
            response = client.get('/api/users/me', headers=headers)

            assert response.status_code == 401
            data = response.get_json()
            assert 'Token expired' in data['error']

    def test_token_required_supports_callable_style(self, app):
        """@token_required without args uses callable shortcut path."""
        from ticket_management_system.resources.users import token_required

        @token_required
        def _view(_token_user):
            return {"ok": True}, 200

        with app.test_request_context("/dummy", headers={"Authorization": "Bearer bad.token"}):
            response = _view()
            assert response[1] == 401


class TestGetAllUsersEndpoint:
    """Test GET /api/users/ endpoint."""

    def test_get_all_users_as_admin(self, client, app, admin_headers, multiple_users):
        """Test getting all users as admin."""
        with app.app_context():
            response = client.get('/api/users/', headers=admin_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert 'users' in data
            assert 'pagination' in data
            assert isinstance(data['users'], list)
            assert len(data['users']) > 0

            # Check pagination metadata
            pagination = data['pagination']
            assert 'page' in pagination
            assert 'per_page' in pagination
            assert 'total_pages' in pagination
            assert 'total_items' in pagination
            assert 'has_next' in pagination
            assert 'has_prev' in pagination

    def test_get_all_users_pagination(self, client, app, admin_headers, multiple_users):
        """Test pagination parameters."""
        with app.app_context():
            response = client.get('/api/users/?page=1&per_page=3', headers=admin_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert len(data['users']) <= 3
            assert data['pagination']['page'] == 1
            assert data['pagination']['per_page'] == 3

    def test_get_all_users_second_page(self, client, app, admin_headers, multiple_users):
        """Test getting second page."""
        with app.app_context():
            response = client.get('/api/users/?page=2&per_page=2', headers=admin_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert data['pagination']['page'] == 2
            assert data['pagination']['has_prev'] is True

    def test_get_all_users_as_regular_user(self, client, app, auth_headers):
        """Token-only access should fail because API key is required."""
        with app.app_context():
            response = client.get('/api/users/', headers=auth_headers)

            assert response.status_code == 401
            data = response.get_json()
            assert data['error'] == 'Unauthorized'
            assert 'x-api-key' in data['message']

    def test_get_all_users_no_token(self, client):
        """Admin endpoint requires API key, not bearer token."""
        response = client.get('/api/users/')

        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Unauthorized'

    def test_get_all_users_invalid_token(self, client):
        """Invalid token is irrelevant without x-api-key."""
        headers = {'Authorization': 'Bearer invalid.token'}
        response = client.get('/api/users/', headers=headers)

        assert response.status_code == 401


class TestUpdateCurrentUserEndpoint:
    """Test PATCH /api/users/me endpoint."""

    def test_update_firstname_only(self, client, auth_headers):
        """Test successfully updating only the firstname field."""
        response = client.patch('/api/users/me',
            json={'firstname': 'UpdatedFirst'},
            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Profile updated successfully'
        assert data['user']['firstname'] == 'UpdatedFirst'
        assert 'user' in data
        assert 'id' in data['user']

    def test_update_lastname_only(self, client, auth_headers):
        """Test successfully updating only the lastname field."""
        response = client.patch('/api/users/me',
            json={'lastname': 'UpdatedLastName'},
            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Profile updated successfully'
        assert data['user']['lastname'] == 'UpdatedLastName'

    def test_update_email_to_unique_value(self, client, auth_headers):
        """Test successfully updating email to a unique value."""
        new_email = 'unique_new_email@example.com'
        response = client.patch('/api/users/me',
            json={'email': new_email},
            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['email'] == new_email

    def test_update_password_field_rejected(self, client, auth_headers):
        """Password updates are no longer part of user profile auth."""
        response = client.patch('/api/users/me',
            json={'password': 'newSecurePassword123'},
            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data['message'] == 'Validation failed'
        assert 'password' in data['errors']

    def test_update_multiple_fields_simultaneously(self, client, auth_headers):
        """Test updating multiple fields in a single request."""
        update_data = {
            'firstname': 'MultiFirst',
            'lastname': 'MultiLast',
            'email': 'multi_update@example.com'
        }
        response = client.patch('/api/users/me',
            json=update_data,
            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['firstname'] == 'MultiFirst'
        assert data['user']['lastname'] == 'MultiLast'
        assert data['user']['email'] == 'multi_update@example.com'

    def test_update_with_empty_json_object(self, client, auth_headers):
        """Test update with empty JSON object returns 400."""
        response = client.patch('/api/users/me',
            json={},
            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Bad Request'

    def test_update_with_null_body(self, client, auth_headers):
        """Test update with null/None body returns 400."""
        response = client.patch('/api/users/me',
            data='',
            content_type='application/json',
            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Bad Request'
        assert 'message' in data

    def test_update_with_json_null_value(self, client, auth_headers):
        """Explicit JSON null hits request body is JSON but None branch."""
        response = client.patch('/api/users/me', json=None, headers=auth_headers)
        assert response.status_code == 400
        assert response.get_json()['error'] == 'Bad Request'

    def test_update_with_invalid_json(self, client, auth_headers):
        """Test update with malformed JSON returns 400."""
        response = client.patch('/api/users/me',
            data='{"invalid": json}',
            content_type='application/json',
            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Bad Request'

    def test_update_email_to_existing_email(self, client, auth_headers, admin_user):
        """Test updating email to one already taken by another user returns 409."""
        response = client.patch('/api/users/me',
            json={'email': admin_user.email},
            headers=auth_headers)

        assert response.status_code == 409
        data = response.get_json()
        assert data['error'] == 'Conflict'
        assert 'already in use' in data['message'].lower()

    def test_update_firstname_exceeds_max_length(self, client, auth_headers):
        """Test firstname validation when exceeding 30 characters."""
        response = client.patch('/api/users/me',
            json={'firstname': 'a' * 31},
            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data['message'] == 'Validation failed'
        assert 'errors' in data
        assert 'firstname' in data['errors']

    def test_update_lastname_exceeds_max_length(self, client, auth_headers):
        """Test lastname validation when exceeding 30 characters."""
        response = client.patch('/api/users/me',
            json={'lastname': 'b' * 31},
            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data['message'] == 'Validation failed'
        assert 'errors' in data
        assert 'lastname' in data['errors']

    def test_update_email_exceeds_max_length(self, client, auth_headers):
        """Test email validation when exceeding 255 characters."""
        long_email = 'a' * 250 + '@example.com'  # Total > 255
        response = client.patch('/api/users/me',
            json={'email': long_email},
            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data['message'] == 'Validation failed'
        assert 'errors' in data
        assert 'email' in data['errors']

    def test_update_password_below_minimum_length_rejected(self, client, auth_headers):
        """Any password field is rejected because password auth was removed."""
        response = client.patch('/api/users/me',
            json={'password': '12345'},
            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data['message'] == 'Validation failed'
        assert 'errors' in data
        assert 'password' in data['errors']

    def test_update_firstname_with_only_whitespace(self, client, auth_headers):
        """Test firstname validation rejects whitespace-only values."""
        response = client.patch('/api/users/me',
            json={'firstname': '   '},
            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data['message'] == 'Validation failed'
        assert 'errors' in data
        assert 'firstname' in data['errors']

    def test_update_email_with_invalid_format(self, client, auth_headers):
        """Test email validation rejects invalid email formats."""
        invalid_emails = [
            'not-an-email',
            'missing@domain',
            '@example.com',
            'user@',
            'user space@example.com'
        ]

        for invalid_email in invalid_emails:
            response = client.patch('/api/users/me',
                json={'email': invalid_email},
                headers=auth_headers)

            assert response.status_code == 400
            data = response.get_json()
            assert 'errors' in data
            assert 'email' in data['errors']

    def test_update_without_authentication(self, client):
        """Test update requires authentication token."""
        response = client.patch('/api/users/me',
            json={'firstname': 'NewName'})

        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Authentication required'

    def test_update_preserves_unchanged_fields(self, client, auth_headers, test_user):
        """Test updating one field doesn't modify other fields."""
        # Store original values
        original_lastname = test_user.lastname
        original_email = test_user.email

        # Update only firstname
        response = client.patch('/api/users/me',
            json={'firstname': 'OnlyFirstChanged'},
            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        # Verify only firstname changed
        assert data['user']['firstname'] == 'OnlyFirstChanged'
        assert data['user']['lastname'] == original_lastname
        assert data['user']['email'] == original_email

    def test_update_updates_timestamp(self, client, auth_headers, test_user):
        """Test that update modifies the updated_at timestamp."""
        import time

        # Get original updated_at
        original_updated_at = test_user.updated_at

        # Wait a moment and update
        time.sleep(0.1)

        response = client.patch('/api/users/me',
            json={'firstname': 'TimestampTest'},
            headers=auth_headers)

        assert response.status_code == 200

        # Refresh user from database
        db.session.refresh(test_user)

        # Verify updated_at changed
        assert test_user.updated_at > original_updated_at

    def test_update_can_keep_same_email(self, client, auth_headers, test_user):
        """Test user can update other fields while keeping the same email."""
        # Update firstname but keep same email
        response = client.patch('/api/users/me',
            json={
                'firstname': 'NewFirst',
                'email': test_user.email  # Same email
            },
            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['firstname'] == 'NewFirst'
        assert data['user']['email'] == test_user.email

    def test_update_firstname_minimum_length(self, client, auth_headers):
        """Test firstname accepts minimum valid length."""
        response = client.patch('/api/users/me',
            json={'firstname': 'A'},
            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['firstname'] == 'A'

    def test_update_password_minimum_length_rejected(self, client, auth_headers):
        """Password field remains rejected even when its length is valid."""
        response = client.patch('/api/users/me',
            json={'password': '123456'},
            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data['message'] == 'Validation failed'
        assert 'password' in data['errors']

    def test_update_profile_unexpected_exception(self, client, auth_headers, monkeypatch):
        """Generic exception branch in update_token_user returns handled 500."""
        monkeypatch.setattr(
            "ticket_management_system.resources.users.UserService.update_user_profile",
            lambda *_a, **_k: (_ for _ in ()).throw(Exception("unexpected")),
        )
        response = client.patch('/api/users/me', json={'firstname': 'New'}, headers=auth_headers)
        assert response.status_code == 500

    def test_update_with_special_characters_in_name(self, client, auth_headers):
        """Test update accepts names with special characters."""
        response = client.patch('/api/users/me',
            json={
                'firstname': "O'Brien",
                'lastname': 'Smith-Jones'
            },
            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['firstname'] == "O'Brien"
        assert data['user']['lastname'] == 'Smith-Jones'

    def test_update_with_unicode_characters(self, client, auth_headers):
        """Test update accepts unicode characters in names."""
        response = client.patch('/api/users/me',
            json={
                'firstname': 'José',
                'lastname': 'Müller'
            },
            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['firstname'] == 'José'
        assert data['user']['lastname'] == 'Müller'

