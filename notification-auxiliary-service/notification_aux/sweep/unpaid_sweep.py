"""Sweep: walk past flights via search (asc by departure), cancel unpaid bookings, deactivate flight."""

from __future__ import annotations

from typing import Any

import requests

from notification_aux.log import logger
from notification_aux.sweep.config import main_api_admin_headers
from notification_aux.sweep.main_api_client import MainTicketApi


def run_unpaid_past_departure_sweep() -> dict[str, Any]:
    """Use flight search until first future departure; for each past *active* flight load bookings and cancel."""
    api = MainTicketApi()
    admin_headers = main_api_admin_headers()

    checked = eligible = cancelled = skipped = 0
    past_flights_marked = 0
    errors: list[str] = []

    for row in api.iter_past_flights_search_departure_asc():
        if row.get("status") != "active":
            continue

        flight_id = str(row.get("id") or "")
        if not flight_id:
            continue
        departure_time = str(row.get("departure_time") or "")

        try:
            detail = api.get_flight(flight_id, include_bookings=True)
        except requests.RequestException as exc:
            errors.append(f"flight_detail_failed:{flight_id}:{exc}")
            continue

        if not detail:
            skipped += 1
            continue

        try:
            if api.set_flight_inactive(admin_headers, flight_id):
                past_flights_marked += 1
                logger.info("[SWEEP] Set flight %s status=inactive", flight_id[:8])
        except requests.RequestException as exc:
            errors.append(f"flight_inactivate_failed:{flight_id}:{exc}")

        for booking in detail.get("bookings") or []:
            if booking.get("booking_status") != "booked":
                continue
            checked += 1
            booking_id = str(booking.get("id") or "")
            if not booking_id:
                skipped += 1
                errors.append("booking_missing_id")
                continue

            eligible += 1
            try:
                cancel_response = api.cancel_booking_as_admin(admin_headers, booking_id)
                if cancel_response.status_code == 200:
                    cancelled += 1
                    logger.info(
                        "[SWEEP] Cancelled unpaid booking #%s (flight departed %s)",
                        booking_id[:8],
                        departure_time,
                    )
                elif cancel_response.status_code in (403, 404, 409):
                    skipped += 1
                else:
                    errors.append(
                        f"cancel_failed:{booking_id}:status_{cancel_response.status_code}"
                    )
            except requests.RequestException as exc:
                errors.append(f"cancel_failed:{booking_id}:{exc}")

    return {
        "checked_unpaid": checked,
        "eligible_for_cancel": eligible,
        "cancelled": cancelled,
        "skipped": skipped,
        "past_flights_marked_inactive": past_flights_marked,
        "errors": errors,
    }
