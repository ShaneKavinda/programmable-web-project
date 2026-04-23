# Notification auxiliary service

Small Flask service used by the main flight API: it accepts booking events over HTTP, logs them as mock email deliveries in SQLite, and can run a periodic job that cancels unpaid bookings after departure and marks past flights inactive via the main API.

## Run locally

```bash
cd notification-auxiliary-service
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python app.py
```

Default: `http://localhost:5051`

## Run with Docker

```bash
docker build -t notification-auxiliary-service .
docker run --rm -p 5051:5051 -e PORT=5051 notification-auxiliary-service
```

Persist the DB with a volume, e.g. `-v notification_aux_data:/app/data` and `-e AUX_DB_PATH=/app/data/notifications.db`.

## Main API wiring

Set on the main API:

- `NOTIFICATION_AUX_BASE_URL` — e.g. `http://localhost:5051` (or the compose service name)
- `NOTIFICATION_AUX_TIMEOUT_SEC` — optional timeout for publish calls

Publishing is best-effort: if this service is down, bookings and payments still succeed.

## HTTP API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/api/events` | Ingest event (`event_type`, `booking_id`, `user_id`, `user_email`; optional `source`, `payload`, `occurred_at`) |
| `GET` | `/api/notifications` | List logs; query `booking_id`, `limit` (1–200, default 50) |
| `GET` | `/api/notifications/<id>` | One log row |

Allowed `event_type` values: `booking_created`, `booking_paid`, `booking_cancelled`.

## Background sweep (optional)

If `BOOKING_SWEEP_ENABLED=true`, a timer calls the main API to clean up unpaid bookings after flight departure and to deactivate flights that are still active but already departed. It needs:

- `MAIN_API_BASE_URL`
- `MAIN_API_ADMIN_API_KEY` (same kind of admin key the main API expects)

Tune interval with `BOOKING_SWEEP_INTERVAL_SECONDS` (seconds, minimum 30). Logs go to stdout (`docker compose logs`).

Naive `departure_time` values from the main API are treated as wall-clock in **`TZ`** (same as Docker / the main app). Set `TZ` if sweep and UI disagree about “past”.

See `.env.example` for a full list of variables.
