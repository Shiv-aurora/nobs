#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
load_images

read -r -p "Arm the budget guard so a 90% notification stops the Mattermost VM? Type ARM: " confirm
[[ "${confirm}" == "ARM" ]] || { echo "Cancelled."; exit 1; }
BUDGET_GUARD_DRY_RUN=false "${SCRIPT_DIR}/deploy-cloud-services.sh"
umask 077
touch "${GCP_DIR}/.budget-guard-armed"
echo "Budget guard armed. Billing notifications are delayed; this reduces risk but cannot guarantee a hard USD 25 ceiling."
