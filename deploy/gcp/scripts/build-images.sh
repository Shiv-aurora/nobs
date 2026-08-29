#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
for command in gcloud docker git; do require_command "${command}"; done
require_tfvars

REGION="$(sed -nE 's/^region[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "${TFVARS_FILE}" | head -1)"
REGION="${REGION:-us-central1}"
PROJECT_ID="$(gcloud config get-value project)"
REPOSITORY="$(tf_output artifact_registry_repository)"
GIT_SHA="$(git -C "${REPO_ROOT}" rev-parse --short=12 HEAD)"
REGISTRY="${REGION}-docker.pkg.dev"
TARGET_PLATFORM="${TARGET_PLATFORM:-linux/amd64}"
AGENT_TAG="${REGISTRY}/${PROJECT_ID}/${REPOSITORY}/agent-service:${GIT_SHA}"
GUARD_TAG="${REGISTRY}/${PROJECT_ID}/${REPOSITORY}/budget-guard:${GIT_SHA}"
MATTERMOST_TAG="${REGISTRY}/${PROJECT_ID}/${REPOSITORY}/noping-mattermost:${GIT_SHA}"

gcloud auth configure-docker "${REGISTRY}" --quiet

docker build --platform "${TARGET_PLATFORM}" --build-arg INSTALL_GOOGLE=true -f "${REPO_ROOT}/agent-service/Dockerfile" -t "${AGENT_TAG}" "${REPO_ROOT}"
docker push "${AGENT_TAG}"
docker pull --platform "${TARGET_PLATFORM}" "${AGENT_TAG}" >/dev/null
AGENT_IMAGE_URI="$(docker inspect --format='{{index .RepoDigests 0}}' "${AGENT_TAG}")"

docker build --platform "${TARGET_PLATFORM}" -t "${GUARD_TAG}" "${REPO_ROOT}/deploy/gcp/budget-guard"
docker push "${GUARD_TAG}"
docker pull --platform "${TARGET_PLATFORM}" "${GUARD_TAG}" >/dev/null
BUDGET_GUARD_IMAGE_URI="$(docker inspect --format='{{index .RepoDigests 0}}' "${GUARD_TAG}")"

docker build --platform "${TARGET_PLATFORM}" -f "${REPO_ROOT}/deploy/mattermost-client/Dockerfile" -t "${MATTERMOST_TAG}" "${REPO_ROOT}"
docker push "${MATTERMOST_TAG}"
docker pull --platform "${TARGET_PLATFORM}" "${MATTERMOST_TAG}" >/dev/null
MATTERMOST_IMAGE_URI="$(docker inspect --format='{{index .RepoDigests 0}}' "${MATTERMOST_TAG}")"

umask 077
cat >"${IMAGES_FILE}" <<EOF
AGENT_IMAGE_URI=${AGENT_IMAGE_URI}
BUDGET_GUARD_IMAGE_URI=${BUDGET_GUARD_IMAGE_URI}
MATTERMOST_IMAGE_URI=${MATTERMOST_IMAGE_URI}
EOF

echo "Wrote immutable image digests to ${IMAGES_FILE}."
