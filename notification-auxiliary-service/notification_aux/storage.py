"""SQLite storage helpers for notification auxiliary service."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager


def db_path() -> str:
    """Resolve sqlite path from env."""
    return os.getenv("AUX_DB_PATH", "./data/notifications.db")


def ensure_db_directory() -> None:
    """Create parent directory for sqlite DB if needed."""
    path = db_path()
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)


@contextmanager
def get_conn():
    """Yield sqlite connection with Row factory."""
    ensure_db_directory()
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create notifications table if missing."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                booking_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_email TEXT NOT NULL,
                source TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                delivery_channel TEXT NOT NULL,
                delivery_message TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                received_at TEXT NOT NULL
            )
            """
        )
