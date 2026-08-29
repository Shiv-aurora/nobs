#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
for command in gcloud terraform tar python; do require_command "${command}"; done
require_tfvars
load_images

INSTANCE="$(tf_output mattermost_instance_name)"
ZONE="$(tf_output zone)"
PROJECT_ID="$(gcloud config get-value project)"
SITE_URL="$(tf_output mattermost_url)"
SITE_ADDRESS="$(tf_output mattermost_site_address)"
LEGACY_IP="$(tf_output mattermost_external_ip)"
MATTERMOST_IMAGE="${MATTERMOST_IMAGE_URI}"
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
GITHUB_WEBHOOK_SECRET="$(gcloud secrets versions access latest --secret="$(tf_output github_webhook_secret_id)" --project="${PROJECT_ID}")"
CALENDAR_CREDENTIALS_JSON=""
if CALENDAR_CREDENTIALS_JSON="$(gcloud secrets versions access latest --secret="$(tf_output google_calendar_credentials_secret_id)" --project="${PROJECT_ID}" 2>/dev/null)"; then
  CALENDAR_CREDENTIALS_B64="$(printf '%s' "${CALENDAR_CREDENTIALS_JSON}" | base64 | tr -d '\n')"
else
  CALENDAR_CREDENTIALS_B64=""
  echo "Google Calendar credentials are not authorized yet; deploying with the deterministic availability fallback."
fi
GITHUB_IDENTITY_MAP="$(tf_output github_identity_map_json)"
GITHUB_REPOSITORY_MAP="$(tf_output github_repository_map_json)"
CALENDAR_IDENTITY_MAP="$(tf_output google_calendar_identity_map_json)"
[[ "${GITHUB_IDENTITY_MAP}" != "{}" ]] || { echo "Configure github_identity_map_json in terraform.tfvars" >&2; exit 1; }
[[ "${GITHUB_REPOSITORY_MAP}" != "{}" ]] || { echo "Configure github_repository_map_json in terraform.tfvars" >&2; exit 1; }
[[ "${CALENDAR_IDENTITY_MAP}" != "{}" ]] || { echo "Configure google_calendar_identity_map_json in terraform.tfvars" >&2; exit 1; }

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"; unset SIGNING_SECRET POSTGRES_PASSWORD ADMIN_PASSWORD DEMO_PASSWORD GITHUB_WEBHOOK_SECRET CALENDAR_CREDENTIALS_JSON CALENDAR_CREDENTIALS_B64 GITHUB_IDENTITY_MAP GITHUB_REPOSITORY_MAP CALENDAR_IDENTITY_MAP' EXIT
install -d -m 0700 "${TMP_DIR}/plugin-bundle"
cp "${GCP_DIR}/vm/docker-compose.yml" "${TMP_DIR}/docker-compose.yml"
cp "${GCP_DIR}/vm/Caddyfile" "${TMP_DIR}/Caddyfile"
cp "${GCP_DIR}/vm/bootstrap.sh" "${TMP_DIR}/bootstrap.sh"
cp -R "${GCP_DIR}/vm/login" "${TMP_DIR}/login"
cp "${BUNDLE}" "${TMP_DIR}/plugin-bundle/"

umask 077
cat >"${TMP_DIR}/.env" <<EOF
MATTERMOST_IMAGE=${MATTERMOST_IMAGE}
MATTERMOST_SITE_URL=${SITE_URL}
NOPING_SITE_ADDRESS=${SITE_ADDRESS}
NOPING_LEGACY_IP=${LEGACY_IP}
NOPING_AGENT_SERVICE_URL=${AGENT_URL}
NOPING_CLOUD_RUN_AUDIENCE=${AGENT_URL}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
NOPING_SERVICE_SIGNING_SECRET=${SIGNING_SECRET}
GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
NOPING_PUBSUB_TOPIC=noping-work-events
NOPING_GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
NOPING_GITHUB_IDENTITY_MAP=${GITHUB_IDENTITY_MAP}
NOPING_GITHUB_REPOSITORY_MAP=${GITHUB_REPOSITORY_MAP}
NOPING_GOOGLE_CALENDAR_CREDENTIALS_B64=${CALENDAR_CREDENTIALS_B64}
NOPING_GOOGLE_CALENDAR_IDENTITY_MAP=${CALENDAR_IDENTITY_MAP}
NOPING_GOOGLE_CALENDAR_ID=primary
NOPING_GOOGLE_CALENDAR_POLL_MINUTES=5
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

echo "NoPing is deployed at ${SITE_URL}"
echo "Demo user: maya (password stored in Secret Manager: $(tf_output demo_user_password_secret_id))"
