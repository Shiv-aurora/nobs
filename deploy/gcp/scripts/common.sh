#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GCP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${GCP_DIR}/../.." && pwd)"
TF_DIR="${GCP_DIR}/terraform"
TFVARS_FILE="${TFVARS_FILE:-${TF_DIR}/terraform.tfvars}"
IMAGES_FILE="${GCP_DIR}/.images.env"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

require_tfvars() {
  [[ -f "${TFVARS_FILE}" ]] || {
    echo "Missing ${TFVARS_FILE}; copy terraform.tfvars.example and fill project_id/billing_account_id." >&2
    exit 1
  }
}

tf_output() {
  terraform -chdir="${TF_DIR}" output -raw "$1"
}

load_images() {
  [[ -f "${IMAGES_FILE}" ]] || {
    echo "Missing ${IMAGES_FILE}; run build-images.sh first." >&2
    exit 1
  }
  # shellcheck disable=SC1090
  source "${IMAGES_FILE}"
  : "${AGENT_IMAGE_URI:?missing AGENT_IMAGE_URI}"
  : "${BUDGET_GUARD_IMAGE_URI:?missing BUDGET_GUARD_IMAGE_URI}"
  : "${ACTION_EXECUTOR_IMAGE_URI:?missing ACTION_EXECUTOR_IMAGE_URI}"
  : "${MATTERMOST_IMAGE_URI:?missing MATTERMOST_IMAGE_URI}"
}
