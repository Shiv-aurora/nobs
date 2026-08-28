#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"
for command in gcloud npm terraform; do require_command "${command}"; done
require_tfvars

PROJECT_ID="$(gcloud config get-value project)"
MATTERMOST_URL="$(tf_output mattermost_url)"
DEMO_PASSWORD_SECRET="$(tf_output demo_user_password_secret_id)"
DEMO_PASSWORD="$(gcloud secrets versions access latest --secret="${DEMO_PASSWORD_SECRET}" --project="${PROJECT_ID}")"

trap 'unset DEMO_PASSWORD' EXIT

MATTERMOST_URL="${MATTERMOST_URL}" \
NOPING_DEMO_USER_PASSWORD="${DEMO_PASSWORD}" \
NOPING_SKIP_RESET="${NOPING_SKIP_RESET:-true}" \
NOPING_CAPTURE_MESSAGING_EVIDENCE="${NOPING_CAPTURE_MESSAGING_EVIDENCE:-true}" \
npm --prefix "${REPO_ROOT}/e2e" test -- "$@"
