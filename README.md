# NoBS

**Fewer pings. Shorter meetings. More actual work.**

NoBS is an AI-native workplace communication layer built on Mattermost. Every employee, project, team, and policy has a permission-aware logical delegate. Routine messages are answered without breaking focus, while attendee agents prepare meetings before humans join.

> **20-second demo:** Maya asks why Atlas is delayed and receives a sourced delegate reply with **0 people interrupted**. In Calendar, agents then resolve the entire engineering sync and recommend cancellation; a second 60-minute launch meeting becomes 15 minutes for one human security decision.

## Why this is not a chatbot

NoBS changes the communication primitive from **message a person** to **express an intent**, and changes meetings from status discovery to bounded human judgment.

```text
Employee question
    ↓
Personal delegate
    ↓
Organization router
    ↓
Project / team / policy delegates
    ↓
Permission-aware evidence + live work state
    ↓
Answer ────────────────or──────────────── Human decision
0 people interrupted                    one complete Needs You card
```

The product includes:

- a real Mattermost Go + React plugin with NoBS-owned channel, message, thread, agent-reply, Calendar, and OOO surfaces;
- employee, project, team, policy, router, and authority delegates;
- evidence-level authorization and restricted-intent denial before retrieval;
- semantic work state projected from normalized GitHub, issue, calendar, and Mattermost events;
- an interruption firewall that separates facts, policy, and human-only decisions;
- OOO-aware authority delegation;
- scoped, expiring decision memory;
- prompt-injection and poisoned-source quarantine;
- Google ADK/Gemini integration with hard call and token budgets;
- Model Armor prompt and response screening;
- Firestore persistence, Pub/Sub ingestion, private Cloud Run, audit telemetry, and a separately permissioned budget guard;
- a Google Cloud-only production path with a maximum `$25/month` project budget target.

## Repository map

```text
plugin/                         Mattermost Go server + React/TypeScript product UI
agent-service/                  FastAPI organizational agent runtime
seed/                           deterministic demo company, evidence, and work events
deploy/local/                   Mattermost + PostgreSQL + agent local Docker stack
deploy/gcp/terraform/           bounded Google Cloud infrastructure
deploy/gcp/scripts/             two-stage deployment and teardown automation
deploy/gcp/budget-guard/        independently permissioned 90% budget shutdown service
deploy/gcp/vm/                  production Mattermost/PostgreSQL/Caddy VM stack
contracts/                      cross-language HMAC contract vectors
docs/                           architecture, security, demo, costs, handoff, evidence
ui-harness/                     browser-validation harness only; not production UI
```

## Core demo path

The seeded organization contains Maya (overnight support), Sarah (security lead), Alex (delegated approver), Daniel (mobile engineer), Priya (product manager), Project Atlas, AUTH-392, SEC-184, and policy SEC-POL-12.

1. **Less Ping** — Maya posts `Why is Atlas delayed?` in `# Project Atlas` without tagging a bot or coworker. NoBS recognizes the scope, routes through project, engineering, and security delegates, and replies inside the native thread without pinging anyone.
2. **Restricted-data refusal** — Maya asks for Sarah’s salary. The request is denied before the HR record is retrieved or sent to Gemini.
3. **Less Meeting: cancel** — attendee, project, Gemini Code Assist, and GitHub agents resolve the Atlas engineering sync and return all 30 minutes.
4. **Less Meeting: compress** — agents resolve engineering and customer context, quarantine malicious agenda content, and reduce launch readiness from 60 to 15 minutes for one authority decision.
5. **OOO and memory** — the profile-menu OOO mode lets the delegate handle routine work and build a return digest; organizer-confirmed outcomes become scoped, expiring knowledge memory.

## Credential-free verification

The sandbox-verifiable suite does not need Docker, Google Cloud, or external credentials:

```bash
make check
```

Individual checks:

```bash
python -m pytest agent-service/tests
(cd deploy/gcp/budget-guard && python -m pytest tests)
(cd plugin && go test ./internal/...)
tsc -p plugin/webapp/tsconfig.sandbox.json --noEmit
python scripts/static_validate.py
python scripts/secret_scan.py
```

The full Mattermost plugin build requires network access once to install Go and npm dependencies:

```bash
./scripts/build-plugin.sh
```

## Local product stack

Requires Docker, Docker Compose, Go, Node 22+, npm, and Python 3.11+.

```bash
cp deploy/local/.env.example deploy/local/.env
./scripts/local-up.sh
```

This starts PostgreSQL, Mattermost Team Edition, the NoBS-branded agent service in deterministic demo mode, installs the plugin, and seeds the demo organization. Open messaging at `http://localhost:8065/acme/channels/project-atlas` or Calendar at `http://localhost:8065/acme/nobs/calendar`.

## Google Cloud deployment

The deployed demo is available at **[35-202-201-122.sslip.io](https://35-202-201-122.sslip.io/)**. Use **Enter demo workspace** for a short-lived, non-admin demo session. The fixed-cost VM is intentionally stopped between demo sessions; run `deploy/gcp/scripts/start-demo.sh` before opening the link. The existing Google Cloud project and internal resource names remain `noping-*` for compatibility. `/nobs` is canonical, while `/noping` remains a legacy redirect.

The production design uses only Google Cloud for deployment:

- Compute Engine: one `e2-small` Mattermost/PostgreSQL/Caddy VM;
- Cloud Run: private ADK/Gemini agent service, `min=0`, `max=1`, concurrency `4`;
- Firestore: compact mutable state, PITR disabled for the hackathon profile;
- Pub/Sub: authenticated work-event delivery and dead-letter handling;
- Model Armor: fail-closed prompt and response screening;
- Secret Manager, Artifact Registry, Cloud Logging, Trace, and Monitoring;
- Cloud Billing budget: `$25`, alerts at 25/50/75/90/100%;
- independent budget guard: stops only the Mattermost VM at 90% after a dry-run test.

Deployment is intentionally two-stage so Terraform never needs a temporary image tag or plaintext secret:

```bash
cp deploy/gcp/terraform/terraform.tfvars.example deploy/gcp/terraform/terraform.tfvars
# Fill project_id and billing_account_id.
deploy/gcp/scripts/deploy-all.sh
# Review dry-run logs, then explicitly arm:
deploy/gcp/scripts/arm-budget-guard.sh
```

## Important documents

- [`VISION.md`](VISION.md) — product thesis and scope
- [`IMPLEMENTATION.md`](IMPLEMENTATION.md) — component and phase plan
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — runtime architecture and failure handling
- [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md) — identities, permissions, injection defense, audit
- [`docs/COST_MODEL.md`](docs/COST_MODEL.md) — enforced limits and shutdown controls
- [`docs/CODEX_HANDOFF.md`](docs/CODEX_HANDOFF.md) — exact Phase 2 execution contract
- [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) — four-minute judging narrative
- [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md) — local and deployed verification evidence
- [`docs/OSS_DISCLOSURE.md`](docs/OSS_DISCLOSURE.md) — open-source provenance

## Phase status

The NoBS build is deployed and browser-verified on Google Cloud: native channels/messages/threads, automatic delegates, a responsive Calendar, two meeting-prep outcomes, a private agent workroom, OOO, security quarantine, organizer-gated Calendar actions, and the complete authority-decision learning loop. The production Playwright suite passes 14 scenarios with one explicitly gated screenshot-only test. Google Cloud bounds remain unchanged (`min=0`, `max=1`, one `e2-small`, and the existing `$25` protection).

## License and attribution

NoBS’s original work is provided under Apache-2.0. Internal plugin IDs retain `noping` for compatibility. The build preserves upstream Mattermost license and notice files outside normal product UI. See [`UPSTREAM.md`](UPSTREAM.md), [`docs/OSS_DISCLOSURE.md`](docs/OSS_DISCLOSURE.md), and [`docs/CONTRIBUTION_MAP.md`](docs/CONTRIBUTION_MAP.md).
