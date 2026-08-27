#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_command gcloud
require_command openssl
require_tfvars

terraform -chdir="${TF_DIR}" output -raw mattermost_instance_name >/dev/null
PROJECT_ID="$(gcloud config get-value project)"

seed_if_empty() {
  local secret_id="$1"
  local bytes="$2"
  if gcloud secrets versions list "${secret_id}" --project "${PROJECT_ID}" --filter='state=ENABLED' --format='value(name)' | grep -q .; then
    echo "Secret ${secret_id} already has an enabled version; leaving it unchanged."
    return
  fi
  local value
  value="$(openssl rand -hex "${bytes}")"
  printf '%s' "${value}" | gcloud secrets versions add "${secret_id}" --project "${PROJECT_ID}" --data-file=- >/dev/null
  unset value
  echo "Added first version for ${secret_id}."
}

seed_if_empty "$(tf_output service_signing_secret_id)" 32
seed_if_empty "$(tf_output postgres_password_secret_id)" 24
seed_if_empty "$(tf_output mattermost_admin_password_secret_id)" 16
seed_if_empty "$(tf_output demo_user_password_secret_id)" 12
seed_if_empty "$(tf_output github_webhook_secret_id)" 32
