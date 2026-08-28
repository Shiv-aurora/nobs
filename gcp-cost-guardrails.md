# Google Cloud Cost Guardrails

This file is the operator-facing cost contract for NoPing Phase 2. The detailed deployed model and latest spend estimate live in [`docs/COST_MODEL.md`](docs/COST_MODEL.md).

Do not increase any limit below without explicit user approval and concrete evidence that the current value prevents the required demo from functioning.

## Hard deployment bounds

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

## Forbidden convenience infrastructure

Do not add Redis, Cloud SQL, GKE, a managed external load balancer, GPUs, recurring snapshots, always-on Cloud Run instances, public Cloud Run IAM, or a second production model path. Do not move production workloads to Railway, Vercel, Supabase, or another non-Google host.

## Operational rules

- Keep the agent and budget-guard Cloud Run services at `min=0`, `max=1`.
- Keep `allUsers` and `allAuthenticatedUsers` out of Cloud Run IAM.
- Keep the budget guard independently permissioned and unable to read business data or create infrastructure.
- Test the 90% notification in dry-run before arming the guard.
- Stop the fixed-cost Mattermost VM after evidence capture unless judging-period uptime has been explicitly approved.
- Use `deploy/gcp/scripts/preflight-cost-check.sh` and `deploy/gcp/scripts/resource-inventory.sh` before and after infrastructure changes.
