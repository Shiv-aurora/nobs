# Google Cloud Cost Model

## Hard boundary

The Google Cloud project budget target is **no more than `$25/month`**. Raising the project budget, machine class, disk ceiling, instance count, model quotas, retention, or service footprint requires explicit user approval.

A Cloud Billing budget is not treated as an instantaneous hard cap. NoPing combines alerts, resource bounds, application admission, automatic shutdown, and teardown.

## Infrastructure profile

| Resource | Bound |
|---|---|
| Mattermost VM | one `e2-small`; `e2-medium` only after measured pressure |
| disk | 20 GB `pd-standard`, maximum 30 GB |
| Cloud Run agent | 1 vCPU, 1 GiB, min 0, max 1, concurrency 4, 120 s |
| Cloud Run budget guard | 1 vCPU, 256 MiB, min 0, max 1, concurrency 1, 30 s |
| Firestore | one native default database, PITR disabled |
| Pub/Sub | work topic, DLQ, budget topic; bounded retention |
| Artifact Registry | keep 3 recent versions; delete untagged after 7 days |
| Redis / Cloud SQL / GKE / load balancer | not used |

The VM stops daily at the configured UTC hour and should be stopped after recording the final demo.

## Application limits

### User and organization

```text
per user:          3/minute, 20/hour, 20/day
per organization: 10/minute, 60/day
concurrent runs:   2
```

### Model per query

```text
maximum model calls:  4
maximum input tokens: 24,000
maximum output tokens: 2,400
maximum delegate hops: 5
```

### Model per day

```text
model calls:   200
input tokens:  1,000,000
output tokens: 100,000
```

Model usage is reserved before the paid call. Unknown provider failures conservatively keep the reservation, preventing restarts or ambiguous errors from hiding possible spend. Permission denials, cached answers, existing decisions, registry reads, navigation, and health checks do not call Gemini.

## Billing controls

Terraform creates a project-filtered `$25` budget with thresholds:

```text
25% · 50% · 75% · 90% · 100%
```

At 90%, an independently permissioned Cloud Run budget guard receives the billing Pub/Sub notification. It validates the expected budget name and ratio. After a synthetic test and explicit `ARM` confirmation, it can only:

- inspect the named Mattermost VM;
- stop Compute instances through a custom role containing `compute.instances.get` and `compute.instances.stop`.

It cannot access Firestore business records, invoke Gemini, alter budgets, create resources, or delete infrastructure. It begins in dry-run.

## Operator commands

```bash
# Validate cost constraints before deployment
deploy/gcp/scripts/preflight-cost-check.sh

# Inspect all planned resources
deploy/gcp/scripts/resource-inventory.sh

# Start only for testing/demo
deploy/gcp/scripts/start-demo.sh

# Stop fixed compute immediately
deploy/gcp/scripts/stop-all.sh

# Destroy the complete stack after evidence is captured
deploy/gcp/scripts/teardown.sh
```

## Phase 2 evidence to append

Codex must record:

- actual project ID and billing scope;
- budget screenshot/output and thresholds;
- VM type/disk/status;
- Cloud Run scaling/concurrency/IAM;
- current accrued cost before recording;
- budget guard dry-run log and armed status;
- effective quota/rate-limit test;
- resource inventory showing no unplanned billable services;
- stop/teardown proof.

Until that evidence is appended, this document describes enforced source configuration—not a claim that resources were provisioned.
