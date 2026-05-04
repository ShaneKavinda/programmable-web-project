#!/bin/sh
set -e

echo "=== Starting Flask Application ==="

# Clear Python bytecode cache to ensure fresh imports
echo "Clearing Python cache..."
find /app -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
find /app -type f -name "*.pyc" -delete 2>/dev/null || true

FLASK_APP_TARGET="app:app"

# Wait for PostgreSQL. AWS deployments use RDS, so derive the host/port from
# DATABASE_URL unless DB_HOST/DB_PORT are explicitly provided.
DB_WAIT_HOST="${DB_HOST:-}"
DB_WAIT_PORT="${DB_PORT:-}"
if [ -z "$DB_WAIT_HOST" ]; then
    DB_WAIT_HOST="$(python -c "from urllib.parse import urlparse; import os; u=urlparse(os.environ.get('DATABASE_URL', '')); print(u.hostname or 'postgres')")"
fi
if [ -z "$DB_WAIT_PORT" ]; then
    DB_WAIT_PORT="$(python -c "from urllib.parse import urlparse; import os; u=urlparse(os.environ.get('DATABASE_URL', '')); print(u.port or 5432)")"
fi

echo "Waiting for PostgreSQL at ${DB_WAIT_HOST}:${DB_WAIT_PORT}..."
while ! nc -z "$DB_WAIT_HOST" "$DB_WAIT_PORT"; do
  sleep 0.5
done
echo "PostgreSQL is ready!"

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
