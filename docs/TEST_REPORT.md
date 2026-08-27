# Phase 1 Test Report

Final credential-free verification date: **2026-08-27**  
Repository marker: **tag `phase1-complete`** (created after final packaging checks)

Phase 2 must append Docker, complete dependency, Terraform-provider, Google Cloud, and production-browser results. This report deliberately separates code that executed in the sandbox from code that could only be statically validated.

## Executed successfully in Phase 1

| Layer | Command | Result |
|---|---|---|
| agent runtime | `python -m pytest agent-service/tests` | **43 passed** |
| budget guard | `(cd deploy/gcp/budget-guard && python -m pytest tests)` | **8 passed** |
| Go deterministic core | `(cd plugin && go test ./internal/...)` | **3 packages passed** |
| React/TypeScript strict check | `tsc -p plugin/webapp/tsconfig.sandbox.json --noEmit` | **passed** |
| Python compilation | `python -m compileall -q agent-service/app deploy/gcp/budget-guard seed scripts` | **passed** |
| shell syntax | `bash -n` across every `scripts/` and `deploy/` shell file | **passed** |
| manifests/HCL contracts | `python scripts/static_validate.py` | **passed** |
| credential scan | `python scripts/secret_scan.py` | **passed** |
| whitespace | `git diff --check` | **passed** |
| aggregate gate | `./scripts/check.sh` | **passed** |

## Behavior covered by automated tests

- factual organizational routing;
- live-status intent;
- policy and decision classification;
- restricted HR request refusal before retrieval/model use;
- prompt-injection refusal before retrieval;
- poisoned-evidence quarantine;
- evidence authorization;
- active and expired delegated authority;
- human-only decision creation and resolution;
- scoped decision memory and facts hashes;
- user, organization, and concurrency rate limits;
- model-call/token reservation and daily ceilings;
- conservative accounting after ambiguous provider failures;
- Google ADK runner contract and usage extraction;
- Model Armor prompt, response, and fail-closed contracts;
- HMAC vectors, replay, target tampering, and demo behavior;
- Pub/Sub envelope parsing, OIDC identity pinning, malformed data, and deduplication;
- persistence adapter restore/write behavior;
- generic semantic work-state projection;
- independent budget notification parsing, dry-run, idempotence, and VM-stop behavior;
- Compute metadata identity-token provider and caching;
- plugin deterministic security packages.

## Broader builds attempted but not claimed

`go test ./...` was attempted. It stopped before compilation because the sandbox could not download the Mattermost/Gorilla modules and the repository intentionally does not invent a `go.sum`. Phase 2 must run `go mod tidy`, commit the generated `go.sum`, and rerun the complete suite.

The webpack production bundle was not attempted without npm dependencies. Phase 2 must run `npm install`, commit `plugin/webapp/package-lock.json`, then run `npm run typecheck`, `npm run build`, and the Mattermost plugin bundle build.

## Statically validated, not executed against providers

- Terraform delimiters, required files, private-IAM constraints, stable Compute address, VM/disk bounds, Cloud Run min/max/concurrency, Firestore PITR disablement, budget thresholds, Billing Budgets Pub/Sub publisher, and application limits;
- Google Cloud deployment shell syntax and two-stage secret/image flow;
- Mattermost/PostgreSQL/Caddy Compose manifests;
- Cloud Run/Firestore/Pub/Sub/Model Armor adapter contracts;
- architecture and OSS disclosure artifacts.

## Not executed in Phase 1

- Docker Compose Mattermost stack;
- complete plugin server build and webpack bundle;
- Terraform `init`, provider-backed `validate`, `plan`, or `apply`;
- `gcloud` deployment scripts;
- real Google ADK/Gemini, Model Armor, Firestore, Pub/Sub, Secret Manager, Cloud Billing, or Compute calls;
- real GitHub and Google Calendar connectors;
- remote GitHub push;
- real Mattermost browser E2E.

CI and [`docs/CODEX_HANDOFF.md`](CODEX_HANDOFF.md) define those required Phase 2 gates. No claim of Google Cloud deployment is made by this report.
