#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose --env-file "$ROOT_DIR/deploy/local/.env" -f "$ROOT_DIR/deploy/local/docker-compose.yml")
BUNDLE="${1:-$ROOT_DIR/plugin/dist/com.noping.enterprise-0.1.0.tar.gz}"
[[ -f "$BUNDLE" ]] || { echo "Plugin bundle not found: $BUNDLE" >&2; exit 1; }

"${COMPOSE[@]}" cp "$BUNDLE" mattermost:/tmp/noping.tar.gz
"${COMPOSE[@]}" exec -T mattermost mmctl --local plugin add /tmp/noping.tar.gz --force
"${COMPOSE[@]}" exec -T mattermost mmctl --local plugin enable com.noping.enterprise

echo "NoPing plugin installed and enabled"
