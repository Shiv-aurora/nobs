#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/local/.env"
[[ -f "$ENV_FILE" ]] || { echo "Copy deploy/local/.env.example to deploy/local/.env first" >&2; exit 1; }
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/deploy/local/docker-compose.yml")

"${COMPOSE[@]}" up -d --build
MATTERMOST_URL="${MATTERMOST_URL:-http://localhost:8065}" "$ROOT_DIR/scripts/wait-for-mattermost.sh"
"$ROOT_DIR/scripts/build-plugin.sh" >/dev/null
"$ROOT_DIR/scripts/install-plugin-local.sh"
"$ROOT_DIR/scripts/ensure-local-admin.sh"
set -a
source "$ENV_FILE"
set +a
python3 "$ROOT_DIR/seed/seed_mattermost.py"
echo "NoPing is ready at ${MATTERMOST_SITE_URL:-http://localhost:8065}/noping"
