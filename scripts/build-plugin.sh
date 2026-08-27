#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/plugin"
command -v go >/dev/null || { echo "go is required" >&2; exit 1; }
command -v npm >/dev/null || { echo "npm is required" >&2; exit 1; }

if [[ ! -d webapp/node_modules ]]; then
  if [[ -f webapp/package-lock.json ]]; then
    npm --prefix webapp ci --no-audit --no-fund
  else
    echo "package-lock.json is not present yet; installing once and asking Codex to commit the generated lockfile." >&2
    npm --prefix webapp install --no-audit --no-fund
  fi
fi
# Ensure sums and modules are reproducible before packaging.
go mod download
go mod verify
make bundle
printf '%s\n' "$ROOT_DIR/plugin/dist/com.noping.enterprise-0.1.0.tar.gz"
