#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_command gcloud
INSTANCE="$(tf_output mattermost_instance_name)"
ZONE="$(tf_output zone)"
PROJECT_ID="$(gcloud config get-value project)"

gcloud compute instances stop "${INSTANCE}" --zone="${ZONE}" --project="${PROJECT_ID}" --quiet >/dev/null 2>&1 || true
echo "Mattermost VM stopped. Cloud Run remains min-instances=0 and incurs request-based cost only when invoked."
