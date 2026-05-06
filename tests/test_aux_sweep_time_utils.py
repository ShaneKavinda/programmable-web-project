"""Regression tests for auxiliary sweep departure parsing."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

AUX_ROOT = Path(__file__).resolve().parents[1] / "notification-auxiliary-service"
sys.path.insert(0, str(AUX_ROOT))

from notification_aux.sweep import time_utils as tu  # noqa: E402


@pytest.fixture
def helsinki_tz(monkeypatch):
    monkeypatch.setenv("TZ", "Europe/Helsinki")


def test_naive_evening_departure_is_past_after_midnight_local(helsinki_tz, monkeypatch):
    """23:54 local same calendar day must be before 00:14 next day local (UTC comparison)."""
    monkeypatch.setattr(
        tu,
        "_utc_now",
        lambda: datetime(2026, 4, 23, 21, 15, tzinfo=timezone.utc),  # Apr 24 00:15 Helsinki (approx)
    )
    assert tu.is_departure_in_past("2026-04-23T23:54:00") is True


def test_naive_evening_not_past_if_utc_now_still_before_departure_utc(helsinki_tz, monkeypatch):
    monkeypatch.setattr(
        tu,
        "_utc_now",
        lambda: datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc),  # well before 23:54 Helsinki -> UTC
    )
    assert tu.is_departure_in_past("2026-04-23T23:54:00") is False


def test_explicit_zulu_string(helsinki_tz, monkeypatch):
    monkeypatch.setattr(
        tu,
        "_utc_now",
        lambda: datetime(2026, 4, 23, 22, 0, tzinfo=timezone.utc),
    )
    assert tu.is_departure_in_past("2026-04-23T21:30:00+00:00") is True
