# PWP SPRING 2026
# PROJECT NAME: Flight Management System (FMS)

## Group Information

- Student 1: Tuukka Palovaara, t6patu01@student.oulu.fi
- Student 2: Shane Dalumura Hettige, sdalumur25@student.oulu.fi
- Student 3: Can Baturlar, cbaturla25@student.oulu.fi

## Overview

This repository contains a flight booking system with three main parts:

- `ticket_management_system/` - Flask REST API, PostgreSQL models, migrations, Swagger docs, Nginx config, and Docker Compose setup.
- `flight-client-app/` - React + Vite frontend client.
- `notification-auxiliary-service/` - Small Flask service for notification logs and the unpaid-booking/past-flight sweep job.

The backend is exposed through Nginx on `http://localhost:8080`. Swagger is available at `http://localhost:8080/apidocs/`.

## Requirements

- Docker and Docker Compose
- Python 3.11+
- Node.js and npm
- Git

## Backend Setup

Create `ticket_management_system/.env` before starting Docker. Typical values:

```env
POSTGRES_DB=flask_db
POSTGRES_USER=flask_user
POSTGRES_PASSWORD=flask_password
SECRET_KEY=change-me
JWT_SECRET_KEY=change-me
ADMIN_API_KEY=change-me-admin-key
```

Optional runtime values:

```env
AUX_BOOKING_SWEEP_ENABLED=true
AUX_BOOKING_SWEEP_INTERVAL_SECONDS=600
GUNICORN_WORKERS=2
GUNICORN_THREADS=2
```

Start the backend, database, Nginx, and auxiliary service:

```bash
docker compose -f ticket_management_system/docker-compose.yml up -d --build
```

Apply database migrations:

```bash
docker compose -f ticket_management_system/docker-compose.yml exec flask-app flask db upgrade --directory ticket_management_system/migrations
```

Populate sample data:

```bash
docker compose -f ticket_management_system/docker-compose.yml exec flask-app python -m ticket_management_system.populate_db
```

Useful commands:

```bash
# Logs
docker compose -f ticket_management_system/docker-compose.yml logs -f

# Backend logs only
docker compose -f ticket_management_system/docker-compose.yml logs -f flask-app

# Database shell
docker compose -f ticket_management_system/docker-compose.yml exec postgres psql -U flask_user -d flask_db

# Stop services
docker compose -f ticket_management_system/docker-compose.yml down
```

## Frontend Setup

```bash
cd flight-client-app
npm install
npm run dev
```

The client runs on `http://localhost:5173` by default.

For local development, set `flight-client-app/.env`:

```env
VITE_API_BASE_URL=http://localhost:8080
```

## AWS Free-Tier Deployment

The AWS Compose file keeps Flask, Nginx, and the notification auxiliary service in Docker, but removes the local PostgreSQL container so the app can use Amazon RDS PostgreSQL.

Before deploying, create new secrets and keep them out of Git:

```bash
cp ticket_management_system/.env.example ticket_management_system/.env
```

For RDS, set `DATABASE_URL` to the private RDS endpoint:

```env
POSTGRES_DB=flask_db
POSTGRES_USER=flask_user
POSTGRES_PASSWORD=your-rds-password
SECRET_KEY=your-new-random-secret
JWT_SECRET_KEY=your-new-random-secret
ADMIN_API_KEY=your-new-random-admin-key
DATABASE_URL=postgresql://flask_user:your-rds-password@your-rds-endpoint.amazonaws.com:5432/flask_db
GUNICORN_WORKERS=1
GUNICORN_THREADS=2
```

Build the React client for same-origin API access:

```bash
cd flight-client-app
cp .env.production.example .env
npm install
npm run build
cd ..
```

Start the AWS stack from the repository root:

```bash
docker compose -f ticket_management_system/docker-compose.aws.yml up -d --build
```

Run migrations against RDS:

```bash
docker compose -f ticket_management_system/docker-compose.aws.yml exec flask-app flask db upgrade --directory ticket_management_system/migrations
```

Optional sample data:

```bash
docker compose -f ticket_management_system/docker-compose.aws.yml exec flask-app python -m ticket_management_system.populate_db
```

Verification endpoints:

```text
http://EC2_PUBLIC_IP/health
http://EC2_PUBLIC_IP/healthz
http://EC2_PUBLIC_IP/apidocs/
```

The AWS Nginx config listens on port `80` and serves `flight-client-app/dist` while proxying `/api/`, `/health`, `/apidocs/`, and Swagger assets to Flask.
Swagger uses the same host that served `/apidocs/`, so "Try it out" works on both local Docker and EC2 without hard-coding a public IP.

## Authentication Notes

The old `POST /api/users/login`, `POST /api/users/register`, and `POST /api/users/token` endpoints have been removed.

Current flow:

- Create bookings without an account-style login flow.
- Issue a user token with `GET /api/users/<user_id>/token`.
- Use `Authorization: Bearer <token>` for user-owned actions.
- In Swagger UI, click **Authorize** and paste the full value `Bearer <token>`, not only the raw token.
- Use `x-api-key: <ADMIN_API_KEY>` for admin-only actions.

Admin routes include user listing, flight create/update/delete, and admin booking cancellation.

## Main API Endpoints

System:

- `GET /`
- `GET /health`
- `GET /healthz`

Users:

- `GET /api/users/<user_id>/token`
- `GET /api/users/me`
- `PATCH /api/users/me`
- `GET /api/users/?page=1&per_page=10` with `x-api-key`

Flights:

- `GET /api/flights/airports`
- `GET /api/flights/search`
- `GET /api/flights/<flight_id>`
- `GET /api/flights/<flight_id>?include_bookings=true`
- `POST /api/flights/` with `x-api-key`
- `PUT /api/flights/<flight_id>` with `x-api-key`
- `DELETE /api/flights/<flight_id>` with `x-api-key`

Bookings:

- `POST /api/bookings/`
- `GET /api/bookings/` with bearer token
- `GET /api/bookings/<booking_id>` with bearer token
- `PUT /api/bookings/<booking_id>` with bearer token
- `DELETE /api/bookings/<booking_id>` with bearer token or `x-api-key`
- `GET /api/bookings/availability?flight_id=<id>&seat_num=<seat>`

Payments:

- `POST /api/payments/` with bearer token

Auxiliary notification logs through the main API:

- `GET /api/aux/notifications?limit=50` with `x-api-key`
- `GET /api/aux/notifications?booking_id=<booking_id>` with `x-api-key`

## Auxiliary Service

The auxiliary service is started automatically by Docker Compose. It stores mock notification deliveries in SQLite and can run a sweep that:

- cancels unpaid bookings after departure
- marks past active flights inactive

It uses the main API through existing endpoints and authenticates with the admin API key. Naive flight times are interpreted using Docker `TZ`, currently `Europe/Helsinki`.

See `notification-auxiliary-service/README.md` for service-specific details.

## Postman

A Postman collection is included:

```text
Programmable_Web_Flight_System.postman_collection.json
```

Import it into Postman and set these collection variables:

- `baseUrl` - usually `http://localhost:8080`
- `adminApiKey` - same value as `ADMIN_API_KEY`
- `userId`, `flightId`, and `bookingId` as needed for specific requests

## Testing

From the repository root:

```bash
python -m pytest tests/ --cov=ticket_management_system --cov-report=html --cov-report=term-missing -q
```

The tests cover API routes, service-layer rules, functional API flows, the notification client, and auxiliary sweep time handling.

Frontend checks:

```bash
cd flight-client-app
npm run build
npm run lint
```

## Project Structure (ROA)

```text
programmable-web-project/
|-- README.md
|-- Programmable_Web_Flight_System.postman_collection.json
|-- flight-client-app/
|-- notification-auxiliary-service/
|-- ticket_management_system/
|   |-- app.py
|   |-- api.py
|   |-- docker-compose.yml
|   |-- Dockerfile
|   |-- gunicorn_config.py
|   |-- migrations/
|   |-- nginx.conf
|   |-- resources/
|   |-- swagger_specs/
|   `-- static/
`-- tests/
```

## AI Usage Declaration

The core API implementation, domain ideas, and system architecture were designed and built by the project team.

AI assistance was used in a supporting role for debugging, refactoring help, README updates, deployment troubleshooting, and test-case drafting. All AI-assisted suggestions were reviewed, edited, and validated by the team before final integration.
