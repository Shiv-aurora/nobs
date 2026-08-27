#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_command gcloud
require_tfvars

PROJECT_ID="$(gcloud config get-value project)"
REGION="${MODEL_ARMOR_LOCATION:-us-central1}"
TEMPLATE_ID="${MODEL_ARMOR_TEMPLATE_ID:-noping-enterprise-guard}"
ENDPOINT="https://modelarmor.${REGION}.rep.googleapis.com/"

gcloud config set api_endpoint_overrides/modelarmor "${ENDPOINT}" >/dev/null

if gcloud model-armor templates describe "${TEMPLATE_ID}" --project="${PROJECT_ID}" --location="${REGION}" >/dev/null 2>&1; then
  echo "Model Armor template ${TEMPLATE_ID} already exists."
  exit 0
fi

gcloud model-armor templates create "${TEMPLATE_ID}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --rai-settings-filters='[{"filterType":"HATE_SPEECH","confidenceLevel":"MEDIUM_AND_ABOVE"},{"filterType":"HARASSMENT","confidenceLevel":"MEDIUM_AND_ABOVE"},{"filterType":"DANGEROUS","confidenceLevel":"MEDIUM_AND_ABOVE"},{"filterType":"SEXUALLY_EXPLICIT","confidenceLevel":"MEDIUM_AND_ABOVE"}]' \
  --basic-config-filter-enforcement=enabled \
  --pi-and-jailbreak-filter-settings-enforcement=enabled \
  --pi-and-jailbreak-filter-settings-confidence-level=HIGH \
  --malicious-uri-filter-settings-enforcement=enabled \
  --template-metadata-custom-llm-response-safety-error-code=798 \
  --template-metadata-custom-llm-response-safety-error-message='NoPing blocked an unsafe model response' \
  --template-metadata-custom-prompt-safety-error-code=799 \
  --template-metadata-custom-prompt-safety-error-message='NoPing blocked an unsafe prompt' \
  --template-metadata-log-sanitize-operations

echo "Created Model Armor template ${TEMPLATE_ID} in ${REGION}."
