#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_command terraform
require_tfvars

terraform -chdir="${TF_DIR}" init -upgrade
terraform -chdir="${TF_DIR}" fmt -recursive
terraform -chdir="${TF_DIR}" validate
terraform -chdir="${TF_DIR}" plan \
  -var-file="${TFVARS_FILE}" \
  -var='deploy_agent_service=false' \
  -var='deploy_budget_guard=false' \
  -out=.stage1.tfplan
terraform -chdir="${TF_DIR}" apply .stage1.tfplan

echo "Stage 1 infrastructure created. Next: seed-secrets.sh, configure-model-armor.sh, build-images.sh."
