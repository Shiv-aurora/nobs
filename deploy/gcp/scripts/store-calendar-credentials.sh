#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
for command in gcloud python; do require_command "${command}"; done
require_tfvars

CREDENTIALS_FILE="${1:?Usage: store-calendar-credentials.sh /path/to/authorized-user.json}"
[[ -f "${CREDENTIALS_FILE}" ]] || { echo "Calendar credentials file not found" >&2; exit 1; }

python - "${CREDENTIALS_FILE}" <<'PY'
import json, pathlib, sys
payload = json.loads(pathlib.Path(sys.argv[1]).read_text())
required = ("client_id", "client_secret", "refresh_token")
if payload.get("type") != "authorized_user" or any(not payload.get(key) for key in required):
    raise SystemExit("Expected authorized_user credentials containing client_id, client_secret, and refresh_token")
PY

PROJECT_ID="$(gcloud config get-value project)"
SECRET_ID="$(tf_output google_calendar_credentials_secret_id)"
gcloud secrets versions add "${SECRET_ID}" \
  --project="${PROJECT_ID}" \
  --data-file="${CREDENTIALS_FILE}" >/dev/null

echo "Stored a new Google Calendar authorized-user credential version in ${SECRET_ID}."
