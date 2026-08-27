#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
for command in gcloud python; do require_command "${command}"; done

PROJECT_ID="$(gcloud config get-value project)"
TOPIC="${NOPING_BUDGET_TOPIC:-$(tf_output budget_updates_topic)}"
BUDGET_NAME="$(tf_output budget_display_name)"
PAYLOAD="$(BUDGET_NAME="${BUDGET_NAME}" python - <<'PY'
import json, os
print(json.dumps({
  "budgetDisplayName": os.environ["BUDGET_NAME"],
  "costAmount": 23.0,
  "budgetAmount": 25.0,
  "alertThresholdExceeded": 0.9,
  "currencyCode": "USD",
}))
PY
)"

gcloud pubsub topics publish "${TOPIC}" --project="${PROJECT_ID}" --message="${PAYLOAD}" >/dev/null
sleep 5
GUARD_SERVICE="$(tf_output budget_guard_service_name)"
REGION="$(tf_output region)"
echo "Published a synthetic 90% budget notification. Inspect Cloud Run logs before arming the guard:"
printf 'gcloud run services logs read %q --region=%q --limit=20\n' "${GUARD_SERVICE}" "${REGION}"
