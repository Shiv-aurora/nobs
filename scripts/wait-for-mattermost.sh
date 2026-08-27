#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${MATTERMOST_URL:-http://localhost:8065}"
for _ in $(seq 1 90); do
  if curl -fsS "$BASE_URL/api/v4/system/ping" >/dev/null 2>&1; then
    echo "Mattermost is ready at $BASE_URL"
    exit 0
  fi
  sleep 2
done
echo "Mattermost did not become ready" >&2
exit 1
