#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/local/.env"
set -a
source "$ENV_FILE"
set +a
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/deploy/local/docker-compose.yml")

"${COMPOSE[@]}" exec -T mattermost mmctl --local user create \
  --email "$MATTERMOST_ADMIN_EMAIL" \
  --username "$MATTERMOST_ADMIN_USERNAME" \
  --password "$MATTERMOST_ADMIN_PASSWORD" \
  --system-admin --email-verified --disable-welcome-email >/dev/null 2>&1 || true
"${COMPOSE[@]}" exec -T mattermost mmctl --local roles system_admin "$MATTERMOST_ADMIN_USERNAME" >/dev/null
# Keep reruns deterministic even if the account already existed.
"${COMPOSE[@]}" exec -T mattermost mmctl --local user change-password "$MATTERMOST_ADMIN_USERNAME" \
  --password "$MATTERMOST_ADMIN_PASSWORD" >/dev/null

echo "Local Mattermost administrator is ready"
