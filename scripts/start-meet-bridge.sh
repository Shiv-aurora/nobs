#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/local/.env"
[[ -f "$ENV_FILE" ]] || { echo "Copy deploy/local/.env.example to deploy/local/.env first" >&2; exit 1; }
set -a
source "$ENV_FILE"
set +a
export NOPING_AGENT_BASE_URL="${NOPING_AGENT_BASE_URL:-http://127.0.0.1:8080}"
export NOPING_MEET_BRIDGE_TOKEN="${NOPING_MEET_BRIDGE_TOKEN:-dev-meet-bridge-token}"
export NOPING_MEET_PROFILE_DIR="${NOPING_MEET_PROFILE_DIR:-$ROOT_DIR/.local/meet-bridge-profile}"
exec "${NOPING_MEET_BRIDGE_PYTHON:-python}" "$ROOT_DIR/meet-bridge/bridge.py"
