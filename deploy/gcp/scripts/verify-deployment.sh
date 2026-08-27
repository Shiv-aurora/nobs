#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
for command in gcloud terraform curl python; do require_command "${command}"; done
PROJECT_ID="$(gcloud config get-value project)"
REGION="$(tf_output region)"
ZONE="$(tf_output zone)"
INSTANCE="$(tf_output mattermost_instance_name)"
MATTERMOST_URL="$(tf_output mattermost_url)"
AGENT_SERVICE="${NOPING_AGENT_SERVICE_NAME:-$(tf_output agent_service_name)}"
BUDGET_GUARD="${NOPING_BUDGET_GUARD_NAME:-$(tf_output budget_guard_service_name)}"

VM_TYPE="$(gcloud compute instances describe "${INSTANCE}" --project="${PROJECT_ID}" --zone="${ZONE}" --format='value(machineType.basename())')"
[[ "${VM_TYPE}" == "e2-small" || "${VM_TYPE}" == "e2-medium" ]] || { echo "Unexpected VM type: ${VM_TYPE}" >&2; exit 1; }

for service in "${AGENT_SERVICE}" "${BUDGET_GUARD}"; do
  DESCRIPTION="$(gcloud run services describe "${service}" --project="${PROJECT_ID}" --region="${REGION}" --format=json)"
  POLICY="$(gcloud run services get-iam-policy "${service}" --project="${PROJECT_ID}" --region="${REGION}" --format=json)"
  python - "${DESCRIPTION}" "${POLICY}" "${service}" <<'PY'
import json, sys
service=json.loads(sys.argv[1]); policy=json.loads(sys.argv[2]); name=sys.argv[3]
scaling=service.get('scaling', {})
assert int(scaling.get('maxInstanceCount', 1)) == 1, f'{name}: max instances must be 1'
assert int(scaling.get('minInstanceCount', 0)) == 0, f'{name}: min instances must be 0'
for binding in policy.get('bindings', []):
    assert 'allUsers' not in binding.get('members', []), 'Cloud Run must not grant allUsers'
    assert 'allAuthenticatedUsers' not in binding.get('members', []), 'Cloud Run must not grant allAuthenticatedUsers'
print(f'Verified {name}: private IAM, min=0, max=1')
PY
done

curl -fsS "${MATTERMOST_URL}/api/v4/system/ping" >/dev/null
terraform -chdir="${TF_DIR}" validate >/dev/null

echo "Deployment verification passed. Mattermost: ${MATTERMOST_URL}/noping"
