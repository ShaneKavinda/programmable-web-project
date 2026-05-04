"""Notification Auxiliary Service"""

from __future__ import annotations

import os

from notification_aux import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5051"))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
