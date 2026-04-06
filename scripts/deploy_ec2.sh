#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:?APP_DIR must be set}"
BRANCH="${BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-ticket_management_system/docker-compose.prod.yml}"
HEALTH_URL="${HEALTH_URL:-http://localhost/healthz}"

echo "Deploying branch ${BRANCH} into ${APP_DIR}"

cd "$APP_DIR"

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

docker compose -f "$COMPOSE_FILE" pull nginx || true
docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans

echo "Waiting for application health check at ${HEALTH_URL}"
for attempt in $(seq 1 24); do
  if curl -fsS "$HEALTH_URL" >/dev/null; then
    echo "Deployment completed successfully."
    exit 0
  fi

  echo "Health check attempt ${attempt}/24 failed, retrying..."
  sleep 5
done

echo "Deployment did not become healthy in time. Recent logs:"
docker compose -f "$COMPOSE_FILE" logs --tail=100
exit 1
