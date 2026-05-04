"""Stdout logging setup for the auxiliary service."""

from __future__ import annotations

import logging
import sys


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] notification-aux: %(message)s",
        stream=sys.stdout,
    )
    # APScheduler logs "next run" in UTC; container logs use local TZ. Keep noise down.
    for name in (
        "apscheduler.scheduler",
        "apscheduler.executors",
        "apscheduler.executors.default",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)
