# Google Cloud Cost Model

## Enforced boundary

The dedicated project **`noping-agentic-shiv-2026`** is bounded to a **$25 monthly target**. Raising the budget, VM class, disk, instance count, retention, model quotas, or service footprint requires explicit approval.

A Cloud Billing budget is not an instantaneous hard cap. NoPing combines alerts, fixed resource ceilings, application admission, daily shutdown, an armed independent guard, and teardown automation.

## Deployed footprint

| Resource | Deployed bound |
|---|---|
| Mattermost VM | one `e2-small` in `us-central1-a`; currently running for demo capture |
| disk | 20 GB `pd-standard` |
| Cloud Run agent | private IAM, 1 vCPU / 1 GiB, min 0, max 1, concurrency 4 |
| Cloud Run budget guard | private IAM, 1 vCPU / 512 MiB, min 0, max 1, concurrency 1 |
| Firestore | one native default database, PITR disabled |
| Pub/Sub | work topic, DLQ, budget topic, bounded subscriptions |
| Artifact Registry | one Docker repository with cleanup policy |
| Redis / Cloud SQL / GKE / load balancer | **not used** |

The final resource inventory matched this list. Both Cloud Run services reported Ready and scale to zero. The VM has a daily stop schedule and must be stopped after recording.

## Application ceilings

```text
per user:          3/minute, 20/hour, 20/day
per organization: 10/minute, 60/day
concurrent runs:   2

per query:         4 model calls, 24,000 input tokens, 2,400 output tokens
per day:           200 model calls, 1,000,000 input tokens, 100,000 output tokens
delegate hops:     5 maximum
```

Operational rate limits and daily model budgets use wall-clock time; the seeded evidence timeline remains deterministic. Usage is reserved before a paid call, and ambiguous provider failures conservatively keep the reservation.

## Billing controls

The project-filtered budget **`NoPing $25 guardrail`** has thresholds at 25%, 50%, 75%, 90%, and 100%. At 90%, Billing publishes to Pub/Sub and the independently permissioned budget guard may only inspect and stop `noping-mattermost` through a custom role.

The guard cannot read Firestore business data, invoke Gemini, alter budgets, create resources, or delete infrastructure. A synthetic notification was tested in dry-run before arming; the deployed setting is now **`dry_run=false`**.

## Spend estimate at handoff

Cloud Billing does not expose real-time accrued cost through the project CLI without a billing export, so no fabricated “current” figure is claimed. As of **2026-08-28 03:00 UTC**, the stack had run for roughly four hours. A conservative estimate for VM compute, 20 GB standard disk allocation, the small number of Gemini/Cloud Run calls, storage, logging, and Pub/Sub traffic is **under $0.25 accrued**.

Even continuous `e2-small` operation plus the disk is roughly in the low teens per month before low-volume serverless/model use; the daily stop schedule reduces that materially. The $25 budget and armed 90% guard remain the authoritative safety boundary.

## Operator commands

```bash
deploy/gcp/scripts/preflight-cost-check.sh
deploy/gcp/scripts/resource-inventory.sh
deploy/gcp/scripts/start-demo.sh
deploy/gcp/scripts/stop-all.sh
deploy/gcp/scripts/teardown.sh
```

`stop-all.sh` stops the sole fixed-cost VM. `teardown.sh` requires the explicit phrase `DESTROY-NOPING` and removes the complete managed stack after evidence is no longer needed.
