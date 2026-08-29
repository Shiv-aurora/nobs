#!/usr/bin/env bash
set -euo pipefail
cd /opt/noping
chmod 0600 .env .bootstrap-secrets
chmod 0755 plugin-bundle
chmod 0644 plugin-bundle/*.tar.gz
set -a
source .bootstrap-secrets
set +a

docker compose --env-file .env pull
docker compose --env-file .env up -d --force-recreate

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8065/api/v4/system/ping >/dev/null; then
    break
  fi
  sleep 3
  if [[ "${i}" == "90" ]]; then
    docker compose --env-file .env logs --tail=200
    exit 1
  fi
done

docker compose --env-file .env exec -T mattermost mmctl --local user create \
  --email admin@noping.local \
  --username admin \
  --password "${MATTERMOST_ADMIN_PASSWORD}" \
  --system-admin \
  --email-verified \
  --disable-welcome-email >/dev/null 2>&1 || true

docker compose --env-file .env exec -T mattermost mmctl --local roles system_admin admin >/dev/null
docker compose --env-file .env exec -T mattermost mmctl --local user change-password admin \
  --password "${MATTERMOST_ADMIN_PASSWORD}" >/dev/null

PLUGIN_FILENAME="$(find ./plugin-bundle -maxdepth 1 -type f -name 'com.noping.enterprise-*.tar.gz' -printf '%f\n' | head -1)"
[[ -n "${PLUGIN_FILENAME}" ]] || { echo "No NoPing plugin bundle mounted" >&2; exit 1; }
PLUGIN_BUNDLE="/plugin-bundle/${PLUGIN_FILENAME}"
docker compose --env-file .env exec -T --user root mattermost mmctl --local plugin add --force "${PLUGIN_BUNDLE}" >/dev/null
docker compose --env-file .env exec -T mattermost mmctl --local plugin enable com.noping.enterprise >/dev/null

systemctl enable noping-compose.service >/dev/null
rm -f .bootstrap-secrets
