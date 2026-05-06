"""Unit tests for auxiliary notification log routes."""

import os


class TestNotificationLogsRoute:
    """Tests for GET /api/aux/notifications endpoint."""

    def test_requires_api_key(self, client):
        """Missing x-api-key should return 401."""
        response = client.get("/api/aux/notifications")

        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "Unauthorized"
        assert "x-api-key" in data["message"]

    def test_rejects_invalid_api_key(self, client):
        """Invalid x-api-key should return 403."""
        response = client.get(
            "/api/aux/notifications",
            headers={"x-api-key": "wrong-key"},
        )

        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == "Forbidden"
        assert "Invalid API key" in data["message"]

    def test_validates_limit_query_param(self, client):
        """Non-integer limit should return 400 before proxy call."""
        response = client.get(
            "/api/aux/notifications?limit=abc",
            headers={"x-api-key": os.environ["ADMIN_API_KEY"]},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "Bad Request"
        assert "limit must be an integer" in data["message"]

    def test_proxies_aux_response_with_default_limit(self, client, monkeypatch):
        """Route should call get_aux_notifications() and forward body/status."""
        captured = {}
        expected_body = {"notifications": [{"event_type": "booking_created"}], "count": 1}

        def fake_get_aux_notifications(booking_id=None, limit=50):
            captured["booking_id"] = booking_id
            captured["limit"] = limit
            return expected_body, 200

        monkeypatch.setattr(
            "ticket_management_system.resources.notification_logs.get_aux_notifications",
            fake_get_aux_notifications,
        )

        response = client.get(
            "/api/aux/notifications",
            headers={"x-api-key": os.environ["ADMIN_API_KEY"]},
        )

        assert response.status_code == 200
        assert response.get_json() == expected_body
        assert captured["booking_id"] is None
        assert captured["limit"] == 50

    def test_proxies_aux_response_with_query_filters(self, client, monkeypatch):
        """Route should pass booking_id and custom limit to client helper."""
        captured = {}
        expected_body = {"error": "Service Unavailable", "message": "Aux down"}

        def fake_get_aux_notifications(booking_id=None, limit=50):
            captured["booking_id"] = booking_id
            captured["limit"] = limit
            return expected_body, 503

        monkeypatch.setattr(
            "ticket_management_system.resources.notification_logs.get_aux_notifications",
            fake_get_aux_notifications,
        )

        response = client.get(
            "/api/aux/notifications?booking_id=abc-123&limit=25",
            headers={"x-api-key": os.environ["ADMIN_API_KEY"]},
        )

        assert response.status_code == 503
        assert response.get_json() == expected_body
        assert captured["booking_id"] == "abc-123"
        assert captured["limit"] == 25

