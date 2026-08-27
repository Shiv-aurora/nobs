#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/plugin"
command -v go >/dev/null || { echo "go is required" >&2; exit 1; }
command -v npm >/dev/null || { echo "npm is required" >&2; exit 1; }

if [[ ! -d webapp/node_modules ]]; then
  npm --prefix webapp ci
fi
# Ensure sums and modules are reproducible before packaging.
go mod download
go mod verify
make bundle
printf '%s\n' "$ROOT_DIR/plugin/dist/com.noping.enterprise-0.1.0.tar.gz"
