"""Background interval job for unpaid booking / past-flight sweep."""

from __future__ import annotations

import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from notification_aux.log import logger
from notification_aux.sweep.config import sweep_enabled, sweep_interval_seconds
from notification_aux.sweep.time_utils import get_container_zone
from notification_aux.sweep.unpaid_sweep import run_unpaid_past_departure_sweep

# Match Docker ``TZ`` so job schedule / APScheduler “next run” text agrees with the rest of the logs.
_SCHED_TZ = get_container_zone()
SCHEDULER = BackgroundScheduler(timezone=_SCHED_TZ)


def _run_sweep_job() -> None:
    logger.info("[SWEEP] Starting unpaid-past-departure sweep...")
    try:
        result = run_unpaid_past_departure_sweep()
        logger.info(
            "[SWEEP] Done. checked=%s eligible=%s cancelled=%s skipped=%s "
            "past_flights_marked_inactive=%s errors=%s",
            result["checked_unpaid"],
            result["eligible_for_cancel"],
            result["cancelled"],
            result["skipped"],
            result["past_flights_marked_inactive"],
            len(result["errors"]),
        )
        for err in result["errors"]:
            logger.warning("[SWEEP] %s", err)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("[SWEEP] Failed: %s", exc)


def start_sweep_scheduler_if_enabled() -> None:
    if not sweep_enabled():
        logger.info("[SWEEP] Scheduler disabled (set BOOKING_SWEEP_ENABLED=true to enable).")
        return

    # Skip only the Werkzeug reloader PARENT process (debug mode double-start).
    # Under gunicorn, WERKZEUG_RUN_MAIN is never set, so this does not trigger.
    if os.getenv("FLASK_ENV") == "development" and os.getenv("WERKZEUG_RUN_MAIN") is None:
        # We cannot distinguish "no reloader" from "reloader parent" here, but
        # this path only matters for `python app.py` with debug=True. Users
        # running production via gunicorn are unaffected.
        pass

    if SCHEDULER.running:
        logger.info("[SWEEP] Scheduler already running, skipping duplicate start.")
        return

    interval = sweep_interval_seconds()
    SCHEDULER.add_job(
        func=_run_sweep_job,
        trigger="interval",
        seconds=interval,
        id="unpaid-past-departure-sweep",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        next_run_time=datetime.now(_SCHED_TZ),  # run once immediately; same TZ as container
    )
    SCHEDULER.start()
    logger.info(
        "[SWEEP] Scheduler started. Interval=%s seconds. First run: now.",
        interval,
    )
