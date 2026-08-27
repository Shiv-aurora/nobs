#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_command terraform
require_tfvars

echo "This destroys the NoPing VM, Firestore database (when Terraform-created), Cloud Run services, topics, secrets, and images."
read -r -p "Type DESTROY-NOPING to continue: " confirm
[[ "${confirm}" == "DESTROY-NOPING" ]] || { echo "Cancelled."; exit 1; }

if [[ -f "${IMAGES_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${IMAGES_FILE}"
fi
terraform -chdir="${TF_DIR}" destroy \
  -var-file="${TFVARS_FILE}" \
  -var="deploy_agent_service=$([[ -n "${AGENT_IMAGE_URI:-}" ]] && echo true || echo false)" \
  -var="deploy_budget_guard=$([[ -n "${BUDGET_GUARD_IMAGE_URI:-}" ]] && echo true || echo false)" \
  -var="agent_image_uri=${AGENT_IMAGE_URI:-}" \
  -var="budget_guard_image_uri=${BUDGET_GUARD_IMAGE_URI:-}"
