# Cost and scaling model

The project remains protected by the existing project-filtered **NoPing $25 guardrail**. A Cloud Billing budget is an alert/control input, not an instantaneous hard cap, so NoBS combines it with fixed infrastructure ceilings and application admission.

## Bounded deployed profile

| Resource | Bound |
|---|---|
| Mattermost/PostgreSQL/Caddy | one `e2-small` VM, existing standard persistent disk |
| private agent Cloud Run | 1 vCPU / 1 GiB, min 0, max 1, concurrency 4 |
| private action executor | 1 vCPU / 512 MiB, min 0, max 1, concurrency 1 |
| private budget guard | min 0, max 1, concurrency 1 |
| Firestore | Native single-region, compact documents/references |
| Pub/Sub | one-day command/work retention; seven-day DLQs |
| meeting mission | four Gemini calls maximum, 24k input / 2.4k output reservation ceiling |
| daily model admission | 200 calls, 1M input, 100k output token ceilings |

Scale-to-zero services add no fixed idle instance charge. The executor’s max-one/single-concurrency profile is intentional for the demo’s consequential write path. Agent Engine Sessions/Memory, Agent Registry, Model Armor, logging, traces, Firestore, Pub/Sub, Artifact Registry, and model usage remain consumption-based and are kept bounded by short retained state and explicit calls.

## Budget controls

The guardrail has 25%, 50%, 75%, 90%, and 100% thresholds. At 90%, Billing publishes to Pub/Sub and the independently permissioned budget guard may inspect and stop only `noping-mattermost`. It cannot read Firestore business data, invoke Gemini, change budgets, create/delete infrastructure, or access secrets. The deployed guard remains armed (`dry_run=false`) after its prior synthetic dry-run proof.

The owner’s broader `$100 Monthly Budget Alert` is separate and does not weaken the project-filtered $25 guardrail.

## Application admission

NoBS checks per-user/per-organization request limits, concurrent runs, and model calls/tokens before provider invocation. Each mission reserves its worst-case four calls and 2,400 output tokens. Successful calls finalize measured usage; interrupted missions conservatively retain the full reservation. When admission is exhausted, deterministic policy, Mattermost collaboration, persisted missions, and cached confirmed decisions continue while new synthesis is denied.

## Scale path

Raise Cloud Run instance bounds only after measuring queue latency and Firestore contention. Move Mattermost/PostgreSQL to standard HA architecture for production. Do not add GKE, a mesh, per-agent services, or a graph/vector database without a measured need.
