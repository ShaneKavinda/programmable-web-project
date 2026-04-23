"""Environment-driven sweep and main-API settings."""

from __future__ import annotations

import os


def sweep_enabled() -> bool:
    return os.getenv("BOOKING_SWEEP_ENABLED", "false").strip().lower() == "true"


def sweep_interval_seconds() -> int:
    raw = os.getenv("BOOKING_SWEEP_INTERVAL_SECONDS", "600").strip()
    try:
        return max(int(raw), 30)
    except ValueError:
        return 600


def main_api_base_url() -> str:
    return os.getenv("MAIN_API_BASE_URL", "http://localhost:8080").rstrip("/")


def main_api_admin_headers() -> dict[str, str]:
    api_key = os.getenv("MAIN_API_ADMIN_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing MAIN_API_ADMIN_API_KEY for auxiliary sweep.")
    return {"x-api-key": api_key}
