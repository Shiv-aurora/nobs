#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"

for command in gcloud terraform docker git python; do
  require_command "${command}"
done
require_tfvars

gcloud auth list --filter=status:ACTIVE --format='value(account)' | grep -q . || {
  echo "No active gcloud identity. Run: gcloud auth login" >&2
  exit 1
}

PROJECT_ID="$(sed -nE 's/^project_id[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "${TFVARS_FILE}" | head -1)"
[[ -n "${PROJECT_ID}" ]] || {
  echo "Could not read project_id from ${TFVARS_FILE}" >&2
  exit 1
}

gcloud projects describe "${PROJECT_ID}" --format='value(projectId)' >/dev/null
gcloud config set project "${PROJECT_ID}" >/dev/null

echo "Preflight passed for project ${PROJECT_ID}."
echo "NoPing budget ceiling in Terraform: USD 25/month."
