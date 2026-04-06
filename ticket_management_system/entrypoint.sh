#!/bin/sh
set -e

echo "=== Starting Flask Application ==="

# Clear Python bytecode cache to ensure fresh imports
echo "Clearing Python cache..."
find /app -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
find /app -type f -name "*.pyc" -delete 2>/dev/null || true

FLASK_APP_TARGET="app:app"

DB_WAIT_TIMEOUT="${DB_WAIT_TIMEOUT:-60}"

DB_WAIT_HOST=$(python - <<'PY'
import os
from urllib.parse import urlparse

database_url = os.environ.get("DATABASE_URL") or "postgresql://flask_user:flask_password@postgres:5432/flask_db"
parsed = urlparse(database_url)
print(parsed.hostname or "postgres")
PY
)

DB_WAIT_PORT=$(python - <<'PY'
import os
from urllib.parse import urlparse

database_url = os.environ.get("DATABASE_URL") or "postgresql://flask_user:flask_password@postgres:5432/flask_db"
parsed = urlparse(database_url)
print(parsed.port or 5432)
PY
)

# Wait for PostgreSQL
echo "Waiting for PostgreSQL at ${DB_WAIT_HOST}:${DB_WAIT_PORT}..."
elapsed=0
while ! nc -z "$DB_WAIT_HOST" "$DB_WAIT_PORT"; do
  sleep 1
  elapsed=$((elapsed + 1))
  if [ "$elapsed" -ge "$DB_WAIT_TIMEOUT" ]; then
    echo "Timed out waiting for PostgreSQL after ${DB_WAIT_TIMEOUT}s"
    exit 1
  fi
done
echo "PostgreSQL is reachable!"

# Run migration commands from the package directory so Flask-Migrate uses
# ticket_management_system/migrations as its default location.
MIGRATIONS_DIR="/app/ticket_management_system/migrations"
if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo "Initializing migrations..."
    (cd /app/ticket_management_system && PYTHONPATH=/app flask --app "$FLASK_APP_TARGET" db init)
fi

# Run migrations
echo "Running database migrations..."
(cd /app/ticket_management_system && PYTHONPATH=/app flask --app "$FLASK_APP_TARGET" db upgrade)

# Start application with Gunicorn configuration
echo "Starting Gunicorn..."
exec gunicorn --config /app/ticket_management_system/gunicorn_config.py ticket_management_system.app:app
