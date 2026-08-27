# NoPing

**Ask the company, not a coworker.**

NoPing is an AI-native workplace communication layer built on Mattermost. Every employee, project, team, and policy has a permission-aware logical delegate. A frontline employee can ask a cross-department question without knowing the org chart; NoPing finds the relevant delegates, retrieves authorized evidence, returns a sourced answer, and interrupts a human only when judgment or formal authority is required.

> **10-second demo:** “Why has Atlas not shipped?” → four organizational delegates consult live project evidence → a sourced answer appears → **0 people interrupted**. A $200K security exception then becomes one complete decision card for the acting approver rather than a burst of messages.

## Why this is not a chatbot

NoPing changes the communication primitive from **message a person** to **express an intent**.

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

- a real Mattermost Go + React plugin with a full-screen NoPing application;
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

1. **Cross-department answer** — Maya asks why Atlas is blocked. NoPing routes through project, engineering, and security delegates, quarantines a malicious uploaded note, and returns evidence without pinging anyone.
2. **Restricted-data refusal** — Maya asks for Sarah’s salary. The request is denied before the HR record is retrieved or sent to Gemini.
3. **Authority-aware escalation** — Maya asks whether a $200K customer opportunity justifies bypassing security review. NoPing refuses to let the model decide, sees Sarah is OOO, validates Alex’s active delegation, and creates one Needs You card.
4. **Organizational memory** — Alex rejects the exception. A materially identical request later uses the scoped decision memory without another interruption; changed facts or expired authority force re-evaluation.

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

This starts PostgreSQL, Mattermost Team Edition, the NoPing agent service in deterministic demo mode, installs the NoPing plugin, and seeds the demo organization. See [`docs/GOOGLE_CLOUD_DEPLOYMENT.md`](docs/GOOGLE_CLOUD_DEPLOYMENT.md) for the production path.

## Google Cloud deployment

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
- [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md) — what was and was not executed in Phase 1
- [`docs/OSS_DISCLOSURE.md`](docs/OSS_DISCLOSURE.md) — open-source provenance

## Phase status

Phase 1 builds and validates the product, plugin boundaries, deterministic orchestration, Google adapters, security controls, infrastructure code, deployment automation, and documentation. Phase 2 must use real credentials to run Docker, install complete dependencies, provision Google Cloud, connect Gemini/ADK and external integrations, perform browser E2E against Mattermost, push GitHub, and capture submission evidence. The exact boundary is documented in [`docs/CODEX_HANDOFF.md`](docs/CODEX_HANDOFF.md).

## License and attribution

NoPing’s original work is provided under Apache-2.0. It imports the Mattermost plugin starter at commit `3296cf6fad808c2372c254cf7b64bcc8a2144e67` and runs the separately distributed Mattermost Team Edition image. See [`UPSTREAM.md`](UPSTREAM.md), [`docs/OSS_DISCLOSURE.md`](docs/OSS_DISCLOSURE.md), and [`docs/CONTRIBUTION_MAP.md`](docs/CONTRIBUTION_MAP.md).
