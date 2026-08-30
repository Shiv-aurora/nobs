# NoBS Architecture Status

Last verified: **2026-08-30 UTC**

This file records observed repository and Google Cloud state. It is updated from executable checks and read-only resource inspection; it is not a roadmap claim.

## Repository baseline

| Item | Verified value |
|---|---|
| repository | `https://github.com/Shiv-aurora/nobs` |
| branch | `main` |
| commit | `4fef547` (`docs: expand deployed architecture`) |
| working tree before architecture work | clean |
| visible product name | NoBS |
| compatibility identifiers | existing `noping-*` resources and plugin IDs remain |

Baseline `./scripts/check.sh` result:

- agent-service Python: **78 passed**;
- budget guard Python: **8 passed**;
- Go plugin packages: **passed**;
- strict TypeScript: **passed**;
- Python compilation, shell syntax, static Terraform/security contracts, credential scan, and Git whitespace: **passed**.

## Verified Google Cloud baseline

| Area | Deployed state |
|---|---|
| project | `noping-agentic-shiv-2026` with billing enabled |
| active operator account | `shivamarora.sa05@gmail.com` |
| region / zone | `us-central1` / `us-central1-a` |
| Mattermost VM | `noping-mattermost`, `e2-small`, 20 GB disk, running during inspection |
| agent gateway | private Cloud Run `noping-agent-service`, revision `noping-agent-service-00011-2zb` |
| agent image | `sha256:7bcd4c7dd8f5f7ce33bdafb52e5af6c3414496f77109a64f18a4e699964e9b7c` |
| agent identity | `noping-agent@noping-agentic-shiv-2026.iam.gserviceaccount.com` |
| budget guard | private Cloud Run `noping-budget-guard`, revision `noping-budget-guard-00008-992` |
| budget guard image | `sha256:4e171c1c774e71f15d7849df3feae56314b4c58889154838151f19d813328ef3` |
| scaling | both Cloud Run services have maximum instances `1`; absent minimum annotation means scale-to-zero |
| Firestore | native `(default)` database in `us-central1`, PITR disabled |
| Model Armor | `noping-enterprise-guard` in `us-central1`; prompt-injection, malicious URI, sensitive-data, and RAI filters enabled; sanitized logging enabled |
| work events | `noping-work-events` with authenticated OIDC push, five-attempt DLQ policy, and `noping-work-events-dlq` inspection subscription |
| budget events | `noping-budget-updates` → authenticated `noping-budget-guard-push` |
| artifacts | Docker repository `us-central1/noping-containers` |
| secrets | six named Secret Manager resources; values were not read |
| project budget | project-filtered `NoPing $25 guardrail` with 25/50/75/90/100% thresholds; broader owner `$100` alert also exists |

Cloud Run IAM is private:

- `noping-agent-service`: invoker is limited to the Mattermost and Pub/Sub push service accounts;
- `noping-budget-guard`: invoker is limited to the Pub/Sub push service account;
- neither service grants `allUsers` or `allAuthenticatedUsers`.

The budget guard uses the custom `nopingBudgetGuard` role containing only `compute.instances.get` and `compute.instances.stop`. Runtime identities have no project Owner or Editor role. The project default Compute service account still has the legacy project Editor grant; deployed NoBS runtimes do not use that identity.

## Qualifying model evidence

The exact primary model is **`gemini-3.5-flash`** at Vertex AI location `global`.

Evidence collected on 2026-08-30:

1. the current Cloud Run revision has `NOPING_GEMINI_MODEL=gemini-3.5-flash`;
2. a bounded request to `projects/noping-agentic-shiv-2026/locations/global/publishers/google/models/gemini-3.5-flash` succeeded and returned `modelVersion: gemini-3.5-flash` with on-demand usage metadata;
3. sanitized Cloud Logging `query.completed` records from revisions `00008` through `00011` contain `model_name=gemini-3.5-flash` for answered production queries.

The repository is not yet consistent with production: `agent-service` defaults, local Compose, Terraform defaults, environment examples, and deployment documentation still contain `gemini-2.5-flash`. This is configuration drift and is the first P0 fix.

The optional Live audio path remains on `gemini-live-2.5-flash-native-audio` and must be disclosed as secondary rather than used as primary mission evidence.

## Firestore inventory

The production root is `organizations/acme`. Observed subcollections and document counts:

| Collection | Documents |
|---|---:|
| `audit` | 220 |
| `config` | 1 |
| `decisions` | 2 |
| `handoff_packets` | 1 |
| `meeting_runs` | 2 |
| `meetings` | 4 |
| `memories` | 2 |
| `ooo_queue` | 24 |
| `queries` | 80 |
| `work_events` | 91 |

Firestore currently persists completed meeting-run documents but does not yet own a transactional mission state machine, individual durable steps, checkpoints, commands, command attempts/results, executable-agent manifests, or preference memory.

## Verified architecture gaps

| Priority | Gap | Evidence |
|---|---|---|
| P0 | source and Terraform model mismatch | production is `gemini-3.5-flash`; checked-in defaults remain `gemini-2.5-flash` |
| P0 | logical delegates are presented as executable agents | `DelegateRegistry` mixes people/projects/teams/policies with router and authority records |
| P0 | simulated route timings | `OrganizationRouter.build_route` contains fixed `duration_ms` values |
| P0 | fixture-selected meeting execution | `MeetingService.prepare` selects `_engineering_run`, `_launch_run`, or `_calendar_run` by meeting ID and returns prewritten turns/conclusions |
| P1 | no durable mission graph | there is no persisted node state machine, retry lease, resume cursor, or per-step transaction |
| P1 | no isolated Action Executor | consequential Calendar writes remain in the Mattermost connector boundary; there is no private executor service or dedicated identity |
| P1 | incomplete event envelope | current `WorkEvent` lacks organization ID, schema version, received time, source resource/version, and trace context |
| P1 | incomplete agent catalog | no typed executable-agent manifest, approval/version/health enforcement, or authenticated admin catalog endpoint |
| P1 | incomplete observability | HTTP spans export through OTLP, but mission/agent/tool/policy/checkpoint/executor spans and trace-linked persisted steps do not exist |
| P2 | Agent Registry not enabled | `agentregistry.googleapis.com` was not enabled at baseline; availability and permissions must be tested before choosing the Firestore fallback |
| P2 | no Agent Runtime, Sessions, Gateway, or Memory Bank resources | only private Cloud Run and Firestore fallbacks are currently deployed |
| P2 | Terraform/deployment drift | Terraform declares a 3600-second agent timeout while the deployed service reports 120 seconds; documentation lists stale revisions/digests |
| P2 | no deployed dashboards or architecture alert policy evidence | Cloud Logging and Trace APIs are enabled, but no NoBS monitoring dashboard was returned by CLI inventory |

## Implementation progress

- [x] Repository and recent history inspected.
- [x] Required architecture, security, data, cost, test, deployment, limitation, submission, and demo documents read.
- [x] Complete credential-free suite passed at baseline.
- [x] Existing Google Cloud project, billing, APIs, compute, Cloud Run, IAM, Firestore, Pub/Sub, secrets, artifacts, Model Armor, logs, and budget inspected.
- [x] Exact Gemini 3.5 model availability and production usage verified.
- [ ] Checked-in model configuration reconciled with production.
- [ ] Delegate Directory separated from Executable Agent Registry.
- [ ] Simulated route and meeting execution removed.
- [ ] Durable governed meeting mission implemented and persisted.
- [ ] Human checkpoint pause/resume and crash recovery proven.
- [ ] Least-privilege Action Executor deployed and verified.
- [ ] Mission-level traces, metrics, and judge-readable UI implemented.
- [ ] Architecture evaluations and production evidence completed.
- [ ] Final diagrams, ADRs, submission text, test report, and demo script reconciled with deployed reality.
