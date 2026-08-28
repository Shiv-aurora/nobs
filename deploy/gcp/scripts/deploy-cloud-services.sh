#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_command terraform
require_tfvars
load_images

ARMED_FILE="${GCP_DIR}/.budget-guard-armed"
DEFAULT_DRY_RUN=true
[[ -f "${ARMED_FILE}" ]] && DEFAULT_DRY_RUN=false
DRY_RUN="${BUDGET_GUARD_DRY_RUN:-${DEFAULT_DRY_RUN}}"
terraform -chdir="${TF_DIR}" plan \
  -var-file="${TFVARS_FILE}" \
  -var='deploy_agent_service=true' \
  -var='deploy_budget_guard=true' \
  -var="agent_image_uri=${AGENT_IMAGE_URI}" \
  -var="budget_guard_image_uri=${BUDGET_GUARD_IMAGE_URI}" \
  -var="budget_guard_dry_run=${DRY_RUN}" \
  -out=.stage2.tfplan
terraform -chdir="${TF_DIR}" apply .stage2.tfplan

echo "Private Cloud Run services deployed. Budget guard dry-run: ${DRY_RUN}."
