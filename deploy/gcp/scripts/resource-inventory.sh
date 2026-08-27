#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_command gcloud
PROJECT_ID="$(gcloud config get-value project)"
REGION="$(tf_output region)"
ZONE="$(tf_output zone)"

echo '== Compute =='
gcloud compute instances list --project="${PROJECT_ID}" --filter='labels.app=noping' --format='table(name,zone.basename(),machineType.basename(),status,networkInterfaces[0].accessConfigs[0].natIP)'
echo '== Cloud Run =='
gcloud run services list --project="${PROJECT_ID}" --region="${REGION}" --filter='metadata.labels.app=noping' --format='table(name,status.url,status.conditions[0].status)'
echo '== Artifact Registry =='
gcloud artifacts repositories list --project="${PROJECT_ID}" --location="${REGION}" --filter='labels.app=noping' --format='table(name,format,mode)'
echo '== Pub/Sub =='
gcloud pubsub topics list --project="${PROJECT_ID}" --filter='labels.app=noping' --format='value(name)'
echo '== Secrets (metadata only) =='
gcloud secrets list --project="${PROJECT_ID}" --filter='labels.app=noping' --format='table(name,createTime)'
echo '== Budget =='
BILLING_ACCOUNT_ID="$(sed -nE 's/^billing_account_id[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "${TFVARS_FILE}" | head -1)"
if [[ -n "${BILLING_ACCOUNT_ID}" ]]; then
  gcloud billing budgets list --billing-account="${BILLING_ACCOUNT_ID}" --format='table(displayName,amount.specifiedAmount.units)'
else
  echo 'Skipped: billing_account_id is blank in terraform.tfvars.'
fi
echo "Inventory complete for ${PROJECT_ID}, ${REGION}, ${ZONE}."
