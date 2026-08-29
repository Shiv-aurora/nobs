#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_command gcloud
INSTANCE="$(tf_output mattermost_instance_name)"
ZONE="$(tf_output zone)"
PROJECT_ID="$(gcloud config get-value project)"
URL="$(tf_output mattermost_url)"

gcloud compute instances start "${INSTANCE}" --zone="${ZONE}" --project="${PROJECT_ID}" --quiet >/dev/null
for _ in $(seq 1 80); do
  if curl -fsS "${URL}/api/v4/system/ping" >/dev/null 2>&1; then
    echo "NoPing is ready: ${URL}/acme/channels/project-atlas"
    exit 0
  fi
  sleep 3
done
echo "VM started, but Mattermost did not become reachable. Check serial output and Docker logs." >&2
exit 1
