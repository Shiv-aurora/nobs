.PHONY: check test test-agent test-guard test-go typecheck local-up local-down plugin-bundle static

check:
	./scripts/check.sh

test: test-agent test-guard test-go

test-agent:
	python -m pytest agent-service/tests

test-guard:
	cd deploy/gcp/budget-guard && python -m pytest tests

test-go:
	cd plugin && go test ./internal/...

typecheck:
	tsc -p plugin/webapp/tsconfig.sandbox.json --noEmit

static:
	python scripts/static_validate.py
	python scripts/secret_scan.py

plugin-bundle:
	./scripts/build-plugin.sh

local-up:
	./scripts/local-up.sh

local-down:
	./scripts/local-down.sh
