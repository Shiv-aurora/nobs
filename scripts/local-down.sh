#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
docker compose --env-file "$ROOT_DIR/deploy/local/.env" -f "$ROOT_DIR/deploy/local/docker-compose.yml" down "$@"
