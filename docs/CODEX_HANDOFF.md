# Codex Phase 2 Handoff

## Mission

Take the Phase 1 repository exactly as delivered, connect the real runtime dependencies, validate it end to end, deploy it entirely on Google Cloud, push the existing Git history to GitHub, and prepare submission evidence.

Do **not** replace Mattermost with a static or standalone HTML app. Do **not** reduce NoPing to an AI sidebar, generic RAG search, or cosmetic multi-agent prompts. Smart compatibility fixes are expected; architectural simplification is not.

## Non-negotiable product behavior

The final demo must show all of these against the real Mattermost plugin and Cloud Run service:

1. Maya asks why Atlas is blocked.
2. The route visibly consults logical person/project/team delegates.
3. Trusted sources support the answer; the malicious source is quarantined.
4. No human is interrupted for the factual query.
5. Salary/compensation is denied before evidence retrieval or model invocation.
6. The `$200K` exception is recognized as human-only authority work.
7. Sarah is OOO and Alex receives the decision through an active delegation.
8. Alex resolves the card.
9. A materially identical request reuses scoped decision memory without a second interruption.
10. Registry, audit, system limits, and Google Cloud proof are visible.

## Non-negotiable architecture

- Mattermost Team Edition + PostgreSQL + Caddy on one Compute Engine VM.
- NoPing Go/React plugin is the product UI and trusted Mattermost boundary.
- Agent runtime is private Cloud Run.
- Gemini 3.5 or newer is called through Google ADK/Vertex AI.
- Firestore persists compact state/memory/audit.
- Pub/Sub uses OIDC push and a dead-letter topic.
- Model Armor screens incoming prompt and final model response.
- Mattermost VM invokes Cloud Run with Google service identity **and** HMAC.
- Production Cloud Run must not grant `allUsers` or `allAuthenticatedUsers`.
- Runtime service account cannot create/resize/stop/delete broad infrastructure.
- Budget guard is separate and can only inspect/stop Compute instances.

## Cost contract

Do not increase these values without explicit user approval:

```text
project budget:                   $25/month
Mattermost VM default:            e2-small
approved measured fallback:       e2-medium
persistent disk:                  20 GB pd-standard (30 GB hard maximum)
Cloud Run agent:                  1 CPU / 1 GiB / min 0 / max 1 / concurrency 4
Cloud Run budget guard:           1 CPU / 256 MiB / min 0 / max 1 / concurrency 1
per user:                         3 queries/min, 20/hour, 20/day
per organization:                 10 queries/min, 60/day
concurrent runs:                  2
model calls/query:                4
input tokens/query:               24,000
output tokens/query:              2,400
model calls/day:                  200
input tokens/day:                 1,000,000
output tokens/day:                100,000
budget guard trigger:             90%
```

Forbidden production additions unless explicitly approved:

- Railway, Vercel, Supabase, Convex;
- Redis;
- Cloud SQL;
- GKE;
- managed external load balancer;
- always-on Cloud Run minimum instances;
- GPUs;
- recurring snapshots/backups;
- public Cloud Run IAM;
- premium model as default;
- parallel Gemini API and Vertex production paths.

## Step 1 — establish the repo remotely

1. Unzip the Phase 1 repository including `.git`.
2. Confirm history and baseline tag:

```bash
git log --oneline --decorate --graph --all
git tag --list
```

Expected baseline tag:

```text
upstream-scaffold-3296cf6
```

3. Create a new GitHub repository owned by the user; do not squash or reinitialize.
4. Add remote and push `main` plus tags.
5. Keep `UPSTREAM.md`, license, and OSS disclosures.

## Step 2 — install and lock dependencies

From a clean environment:

```bash
cd plugin/webapp
npm install --no-audit --no-fund
npm run typecheck
npm run build
cd ../..
```

Commit the generated `plugin/webapp/package-lock.json`.

Then:

```bash
cd plugin
go mod tidy
go mod verify
go test ./...
cd ..
```

Commit `plugin/go.sum` and any `go.mod` normalization. Do not change dependency majors just to silence warnings.

Install Python environments and run tests:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e './agent-service[test,google]'
pip install -e './deploy/gcp/budget-guard[test]'
make check
```

## Step 3 — build the real Mattermost stack locally

```bash
cp deploy/local/.env.example deploy/local/.env
./scripts/local-up.sh
```

Validate:

- Mattermost login;
- plugin installed/enabled;
- `/noping` renders the React product route;
- all primary demo flows work in deterministic demo mode;
- browser console has no errors;
- refresh/deep links work;
- Rooms fallback opens Mattermost normally;
- plugin server never trusts a browser-supplied requester ID.

Use Playwright for E2E. Add tests under `e2e/` and commit them.

## Step 4 — validate Terraform before apply

Install Terraform 1.16.x and run:

```bash
terraform -chdir=deploy/gcp/terraform fmt -recursive
terraform -chdir=deploy/gcp/terraform init -backend=false
terraform -chdir=deploy/gcp/terraform validate
```

Fix real provider/API mismatches while preserving the architecture and limits. Run `make check` after every change.

Copy variables:

```bash
cp deploy/gcp/terraform/terraform.tfvars.example deploy/gcp/terraform/terraform.tfvars
```

Set project and billing account. Use a dedicated project if possible.

Run:

```bash
deploy/gcp/scripts/preflight.sh
deploy/gcp/scripts/preflight-cost-check.sh
```

## Step 5 — deploy in two stages

Use:

```bash
deploy/gcp/scripts/deploy-all.sh
```

Expected sequence:

- stage-one Terraform creates APIs, identities, network, a stable external address, VM, topics, Firestore, registry, secret containers, and budget;
- secrets are generated locally and added as Secret Manager versions—not Terraform values;
- Model Armor template is configured;
- both images are pushed and immutable digests recorded outside Git;
- stage-two Terraform deploys private Cloud Run and authenticated subscriptions;
- Mattermost/plugin bundle uploads via IAP, uses the Terraform-selected pinned Mattermost image, and seeds demo users/data;
- synthetic budget event runs with guard still dry-run;
- deployment verification runs.

Never paste secret values into source, Terraform variables, shell history, screenshots, or chat.

## Step 6 — real Google integrations

### Gemini + ADK

Confirm:

- `GOOGLE_GENAI_USE_VERTEXAI=TRUE`;
- required Gemini 3.5+ model is available in selected region/project;
- `GoogleADKModel` runs through the actual ADK runner contract;
- usage metadata is captured and reconciled;
- query result identifies the real model;
- model is not called for denials, existing decisions, or cached answers.

If the exact model identifier differs, change only `gemini_model`/environment and document the verified identifier.

### Model Armor

- run `configure-model-armor.sh`;
- confirm prompt and response operations;
- test malicious prompt and malicious source;
- preserve fail-closed behavior;
- capture logs/screenshots without leaking source bodies.

### Firestore

- verify decisions/memory/events/audit survive Cloud Run cold start;
- ensure no PITR/backups/managed TTL were enabled;
- inspect indexes and avoid indexing large content.

### Pub/Sub

- publish `seed/demo_events.json` events;
- verify OIDC push identity/audience;
- verify duplicate delivery is a no-op;
- force malformed/failing event and show DLQ behavior.

### GitHub and Google Calendar

Implement production connectors behind the normalized `WorkEvent` contract:

- GitHub: least-privilege webhook or app, signature verification, PR/review/status normalization;
- Calendar: OAuth/service account/domain-delegation only if authorized; fetch approved OOO/availability events, then normalize;
- do not expose private calendar descriptions beyond necessary availability/delegation fields;
- maintain a configured identity map from external account to Mattermost/NoPing user;
- keep seeded events as deterministic fallback for the judging demo.

Do not delay the working submission for a broad Jira integration. A GitHub event and Calendar OOO path are sufficient real connectors if robust.

## Step 7 — run security and cost acceptance

Required proofs:

- Cloud Run IAM has only VM and Pub/Sub invokers;
- unauthenticated request is rejected;
- wrong HMAC/body/replay is rejected;
- salary query has no evidence/model call;
- malicious source is quarantined;
- decision cannot be resolved by Maya;
- expired/invalid delegation is rejected;
- per-user limit returns `429`;
- daily model limit blocks before provider call;
- AI disabled state preserves deterministic features;
- Cloud Run min/max/concurrency match contract;
- resource inventory contains no unplanned service;
- budget guard synthetic 90% notification logs intended stop while dry-run.

Only after reviewing the dry-run:

```bash
deploy/gcp/scripts/arm-budget-guard.sh
```

Append evidence to `docs/TEST_REPORT.md` and `docs/COST_MODEL.md`.

## Step 8 — visual and product polish

Do not redesign toward conventional Slack. Preserve:

- Ask Your Company as primary surface;
- Needs You instead of unread-count obsession;
- visible delegate route;
- evidence/freshness/confidence;
- `people interrupted` outcome;
- project/team/person semantic state;
- Rooms as fallback.

Polish responsive behavior, loading states, errors, focus, keyboard navigation, empty states, and browser deep links. The final product should look like a company application, not a demo dashboard.

## Step 9 — submission evidence

Capture:

- hosted URL and judge credentials;
- Cloud Run service/logs and private IAM;
- Gemini/ADK execution;
- Model Armor block;
- Firestore state;
- Pub/Sub event and DLQ;
- VM/Compute proof;
- `$25` budget thresholds and budget-guard dry-run;
- architecture diagram;
- clean GitHub repo and reproducible README.

Record the four-minute video using `docs/DEMO_SCRIPT.md`. Keep it public on YouTube/Vimeo and show Google Cloud proof in the first four minutes.

## Completion definition

Phase 2 is complete only when:

- clean clone builds;
- local Docker E2E passes;
- Terraform validates and applies;
- deployed Mattermost route works;
- real Gemini/ADK call works;
- security/cost gates pass;
- repo and tags are pushed;
- final screenshots/video/Devpost fields are ready;
- VM is stopped after recording unless the user explicitly approves judging-period uptime.
