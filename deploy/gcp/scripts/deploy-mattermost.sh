#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
for command in gcloud terraform tar python; do require_command "${command}"; done
require_tfvars

INSTANCE="$(tf_output mattermost_instance_name)"
ZONE="$(tf_output zone)"
PROJECT_ID="$(gcloud config get-value project)"
SITE_URL="$(tf_output mattermost_url)"
SITE_ADDRESS="$(tf_output mattermost_site_address)"
MATTERMOST_IMAGE="$(tf_output mattermost_image)"
AGENT_URL="$(tf_output agent_service_url)"
[[ -n "${AGENT_URL}" ]] || {
  echo "Cloud Run agent service is not deployed; run deploy-cloud-services.sh first." >&2
  exit 1
}

BUNDLE="$("${REPO_ROOT}/scripts/build-plugin.sh" | tail -n 1)"
[[ -f "${BUNDLE}" ]] || { echo "Plugin bundle not found: ${BUNDLE}" >&2; exit 1; }

SIGNING_SECRET="$(gcloud secrets versions access latest --secret="$(tf_output service_signing_secret_id)" --project="${PROJECT_ID}")"
POSTGRES_PASSWORD="$(gcloud secrets versions access latest --secret="$(tf_output postgres_password_secret_id)" --project="${PROJECT_ID}")"
ADMIN_PASSWORD="$(gcloud secrets versions access latest --secret="$(tf_output mattermost_admin_password_secret_id)" --project="${PROJECT_ID}")"
DEMO_PASSWORD="$(gcloud secrets versions access latest --secret="$(tf_output demo_user_password_secret_id)" --project="${PROJECT_ID}")"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"; unset SIGNING_SECRET POSTGRES_PASSWORD ADMIN_PASSWORD DEMO_PASSWORD' EXIT
install -d -m 0700 "${TMP_DIR}/plugin-bundle"
cp "${GCP_DIR}/vm/docker-compose.yml" "${TMP_DIR}/docker-compose.yml"
cp "${GCP_DIR}/vm/Caddyfile" "${TMP_DIR}/Caddyfile"
cp "${GCP_DIR}/vm/bootstrap.sh" "${TMP_DIR}/bootstrap.sh"
cp "${BUNDLE}" "${TMP_DIR}/plugin-bundle/"

umask 077
cat >"${TMP_DIR}/.env" <<EOF
MATTERMOST_IMAGE=${MATTERMOST_IMAGE}
MATTERMOST_SITE_URL=${SITE_URL}
NOPING_SITE_ADDRESS=${SITE_ADDRESS}
NOPING_AGENT_SERVICE_URL=${AGENT_URL}
NOPING_CLOUD_RUN_AUDIENCE=${AGENT_URL}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
NOPING_SERVICE_SIGNING_SECRET=${SIGNING_SECRET}
EOF
cat >"${TMP_DIR}/.bootstrap-secrets" <<EOF
MATTERMOST_ADMIN_PASSWORD=${ADMIN_PASSWORD}
NOPING_DEMO_USER_PASSWORD=${DEMO_PASSWORD}
EOF

tar -C "${TMP_DIR}" --exclude='noping-vm.tgz' -czf "${TMP_DIR}/noping-vm.tgz" .

gcloud compute instances start "${INSTANCE}" --zone="${ZONE}" --project="${PROJECT_ID}" >/dev/null 2>&1 || true
gcloud compute ssh "${INSTANCE}" --zone="${ZONE}" --project="${PROJECT_ID}" --tunnel-through-iap \
  --command='rm -f /tmp/noping-vm.tgz' >/dev/null
gcloud compute scp "${TMP_DIR}/noping-vm.tgz" "${INSTANCE}:/tmp/noping-vm.tgz" \
  --zone="${ZONE}" --project="${PROJECT_ID}" --tunnel-through-iap --quiet

gcloud compute ssh "${INSTANCE}" --zone="${ZONE}" --project="${PROJECT_ID}" --tunnel-through-iap --command='
set -euo pipefail
sudo systemctl stop noping-compose.service >/dev/null 2>&1 || true
if [ -f /opt/noping/docker-compose.yml ]; then cd /opt/noping && sudo docker compose --env-file .env down || true; fi
sudo rm -rf /opt/noping
sudo install -d -m 0750 /opt/noping
sudo tar -xzf /tmp/noping-vm.tgz -C /opt/noping
sudo chmod 0750 /opt/noping/bootstrap.sh
sudo /opt/noping/bootstrap.sh
rm -f /tmp/noping-vm.tgz
'

MATTERMOST_URL="${SITE_URL}" \
MATTERMOST_ADMIN_USERNAME=admin \
MATTERMOST_ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
NOPING_DEMO_USER_PASSWORD="${DEMO_PASSWORD}" \
python "${REPO_ROOT}/seed/seed_mattermost.py"

echo "Mattermost and the NoPing plugin are deployed at ${SITE_URL}/noping"
echo "Demo user: maya (password stored in Secret Manager: $(tf_output demo_user_password_secret_id))"
