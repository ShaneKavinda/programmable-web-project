"""Register HTTP blueprints on the Flask app."""

from __future__ import annotations

from flask import Flask

from notification_aux.routes import events, health, notifications


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health.bp)
    app.register_blueprint(events.bp)
    app.register_blueprint(notifications.bp)
