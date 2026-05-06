"""Unit tests for auxiliary notification client helpers."""

from unittest.mock import Mock

import requests

from ticket_management_system.resources import notification_client


class TestPublishBookingEvent:
    """Tests for publish_booking_event()."""

    def test_returns_false_when_base_url_missing(self, monkeypatch):
        """Publishing is disabled when auxiliary URL is not configured."""
        monkeypatch.setenv("NOTIFICATION_AUX_BASE_URL", "")

        result = notification_client.publish_booking_event(
            event_type="booking_created",
            booking_id="booking-1",
            user_id="user-1",
            user_email="user@example.com",
        )

        assert result is False

    def test_posts_event_and_returns_true_for_non_5xx(self, monkeypatch):
        """Client should treat non-5xx responses as successful best-effort publish."""
        monkeypatch.setenv("NOTIFICATION_AUX_BASE_URL", "http://aux-service:5002")
        monkeypatch.setenv("NOTIFICATION_AUX_TIMEOUT_SEC", "2.5")
        post_mock = Mock(return_value=Mock(status_code=202))
        monkeypatch.setattr(notification_client.requests, "post", post_mock)

        result = notification_client.publish_booking_event(
            event_type="booking_paid",
            booking_id="booking-2",
            user_id="user-2",
            user_email="u2@example.com",
            payload={"total_price": "100.00"},
        )

        assert result is True
        post_mock.assert_called_once()
        call_args = post_mock.call_args
        assert call_args.kwargs["json"]["event_type"] == "booking_paid"
        assert call_args.kwargs["json"]["booking_id"] == "booking-2"
        assert call_args.kwargs["json"]["user_id"] == "user-2"
        assert call_args.kwargs["json"]["user_email"] == "u2@example.com"
        assert call_args.kwargs["timeout"] == 2.5
        assert call_args.args[0] == "http://aux-service:5002/api/events"

    def test_returns_false_on_request_exception(self, monkeypatch):
        """Network failures should not break caller behavior."""
        monkeypatch.setenv("NOTIFICATION_AUX_BASE_URL", "http://aux-service:5002")

        def _raise_request_exception(*_args, **_kwargs):
            raise requests.RequestException("connection failed")

        monkeypatch.setattr(notification_client.requests, "post", _raise_request_exception)

        result = notification_client.publish_booking_event(
            event_type="booking_cancelled",
            booking_id="booking-3",
            user_id="user-3",
            user_email="u3@example.com",
        )

        assert result is False


class TestGetAuxNotifications:
    """Tests for get_aux_notifications()."""

    def test_returns_503_when_base_url_missing(self, monkeypatch):
        """Reading logs requires configured auxiliary base URL."""
        monkeypatch.setenv("NOTIFICATION_AUX_BASE_URL", "")

        body, code = notification_client.get_aux_notifications()

        assert code == 503
        assert body["error"] == "Service Unavailable"
        assert "NOTIFICATION_AUX_BASE_URL" in body["message"]

    def test_calls_aux_endpoint_with_clamped_limit_and_filter(self, monkeypatch):
        """Limit should be clamped to API bounds and booking filter forwarded."""
        monkeypatch.setenv("NOTIFICATION_AUX_BASE_URL", "http://aux-service:5002/")
        monkeypatch.setenv("NOTIFICATION_AUX_TIMEOUT_SEC", "1.0")
        expected_payload = {"notifications": [{"id": "n1"}], "count": 1}
        get_mock = Mock(return_value=Mock(status_code=200, json=Mock(return_value=expected_payload)))
        monkeypatch.setattr(notification_client.requests, "get", get_mock)

        body, code = notification_client.get_aux_notifications(
            booking_id="booking-abc",
            limit=999,  # should clamp to 200
        )

        assert code == 200
        assert body == expected_payload
        get_mock.assert_called_once()
        call_args = get_mock.call_args
        assert call_args.args[0] == "http://aux-service:5002/api/notifications"
        assert call_args.kwargs["params"]["booking_id"] == "booking-abc"
        assert call_args.kwargs["params"]["limit"] == 200
        assert call_args.kwargs["timeout"] == 3.0

    def test_returns_503_on_request_exception(self, monkeypatch):
        """Client should surface auxiliary connectivity errors consistently."""
        monkeypatch.setenv("NOTIFICATION_AUX_BASE_URL", "http://aux-service:5002")

        def _raise_request_exception(*_args, **_kwargs):
            raise requests.RequestException("timeout")

        monkeypatch.setattr(notification_client.requests, "get", _raise_request_exception)

        body, code = notification_client.get_aux_notifications(limit=0)  # should clamp to 1

        assert code == 503
        assert body["error"] == "Service Unavailable"
        assert "Could not reach auxiliary service" in body["message"]

