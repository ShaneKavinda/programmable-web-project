"""Notification auxiliary service package."""

from __future__ import annotations

from flask import Flask

from notification_aux.log import logger
from notification_aux.logging_config import configure_logging
from notification_aux.routes import register_blueprints
from notification_aux.storage import init_db
from notification_aux.sweep.scheduler import start_sweep_scheduler_if_enabled


def create_app() -> Flask:
    configure_logging()
    init_db()
    app = Flask(__name__)
    register_blueprints(app)
    logger.info("Notification auxiliary service started.")
    start_sweep_scheduler_if_enabled()
    return app
