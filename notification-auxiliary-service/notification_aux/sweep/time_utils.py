"""Parse flight departure times for sweep logic."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def get_container_zone() -> ZoneInfo:
    """Container / process timezone (``TZ``), e.g. Docker `Europe/Helsinki`."""
    tz_name = (os.getenv("TZ") or "").strip() or "Europe/Helsinki"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("Europe/Helsinki")


def _naive_departure_zone() -> ZoneInfo:
    """Interpret API departure strings that have no UTC offset.

    The main API stores naive datetimes (Postgres without time zone); they are
    wall-clock in the same zone as the API / operators (Docker sets TZ).
    Previously we treated naive values as UTC, which made evening local
    departures look hours in the future compared to real UTC "now".
    """
    return get_container_zone()


def parse_iso_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _utc_now() -> datetime:
    """Wall-clock UTC "now" (overridable in tests)."""
    return datetime.now(timezone.utc)


def is_departure_in_past(departure_iso: str) -> bool:
    dt = parse_iso_datetime(departure_iso)
    if dt is None:
        return False
    if dt.tzinfo is None:
        dt_utc = dt.replace(tzinfo=_naive_departure_zone()).astimezone(timezone.utc)
    else:
        dt_utc = dt.astimezone(timezone.utc)
    return dt_utc < _utc_now()
