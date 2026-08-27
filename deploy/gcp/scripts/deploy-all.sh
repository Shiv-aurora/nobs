#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"${SCRIPT_DIR}/preflight.sh"
"${SCRIPT_DIR}/bootstrap-infra.sh"
"${SCRIPT_DIR}/seed-secrets.sh"
"${SCRIPT_DIR}/configure-model-armor.sh"
"${SCRIPT_DIR}/build-images.sh"
BUDGET_GUARD_DRY_RUN=true "${SCRIPT_DIR}/deploy-cloud-services.sh"
"${SCRIPT_DIR}/deploy-mattermost.sh"
"${SCRIPT_DIR}/test-budget-guard.sh"
"${SCRIPT_DIR}/verify-deployment.sh"

echo "Deployment complete with the budget guard still in dry-run. Review its log, then run arm-budget-guard.sh."
