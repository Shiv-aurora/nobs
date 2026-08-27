#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo '== Python agent runtime =='
python -m pytest agent-service/tests

echo '== Budget guard =='
(
  cd deploy/gcp/budget-guard
  python -m pytest tests
)

echo '== Go plugin and connector runtime =='
(
  cd plugin
  GOCACHE="${TMPDIR:-/tmp}/noping-go-cache" go test ./...
)

echo '== Strict TypeScript =='
npm --prefix plugin/webapp run typecheck

echo '== Python compilation =='
python -m compileall -q agent-service/app deploy/gcp/budget-guard seed scripts

echo '== Shell syntax =='
while IFS= read -r -d '' file; do bash -n "${file}"; done < <(find scripts deploy -type f -name '*.sh' -print0)

echo '== Static manifests / Terraform contracts =='
python scripts/static_validate.py

echo '== Credential scan =='
python scripts/secret_scan.py

echo '== Git whitespace =='
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
else
  echo 'Skipped: source archive has no Git metadata.'
fi

echo 'All credential-free Phase 1 checks passed.'
