"""HTTP client for the main ticket API"""

from __future__ import annotations

from typing import Any, Iterator

import requests

from notification_aux.sweep.config import main_api_base_url
from notification_aux.sweep.time_utils import is_departure_in_past


class MainTicketApi:
    """Uses flight search/detail, flight update, and booking delete on the main API."""

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()

    @property
    def base_url(self) -> str:
        return main_api_base_url()

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def iter_past_flights_search_departure_asc(self) -> Iterator[dict[str, Any]]:
        """Paginate GET /api/flights/search (active statuses), sorted by departure ascending.

        Yields only rows whose departure_time is in the past. Stops fetching further
        pages once a row with departure in the future is seen (later rows are later).
        """
        page = 1
        per_page = 100
        while True:
            response = self._session.get(
                self._url("/api/flights/search"),
                params={
                    "status": "active",
                    "page": page,
                    "per_page": per_page,
                    "sort_by": "departure_time",
                    "sort_order": "asc",
                },
                timeout=30,
            )
            response.raise_for_status()
            body = response.json()
            flights = body.get("flights") or []

            for flight in flights:
                dep = str(flight.get("departure_time") or "")
                if not dep:
                    continue
                if not is_departure_in_past(dep):
                    return
                yield flight

            pagination = body.get("pagination") or {}
            if not pagination.get("has_next"):
                return
            page += 1

    def get_flight(self, flight_id: str, *, include_bookings: bool = False) -> dict[str, Any] | None:
        params = {}
        if include_bookings:
            params["include_bookings"] = "true"
        response = self._session.get(
            self._url(f"/api/flights/{flight_id}"),
            params=params or None,
            timeout=10,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json().get("flight")

    def set_flight_inactive(self, admin_headers: dict[str, str], flight_id: str) -> bool:
        response = self._session.put(
            self._url(f"/api/flights/{flight_id}"),
            headers=admin_headers,
            json={"status": "inactive"},
            timeout=10,
        )
        if response.status_code in (200, 404):
            return response.status_code == 200
        response.raise_for_status()
        return True

    def cancel_booking_as_admin(
        self, admin_headers: dict[str, str], booking_id: str
    ) -> requests.Response:
        """DELETE /api/bookings/{id} with ``x-api-key`` (admin may cancel any booking)."""
        return self._session.delete(
            self._url(f"/api/bookings/{booking_id}"),
            headers=admin_headers,
            timeout=10,
        )
