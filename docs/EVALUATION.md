# Architecture evaluation

The credential-free suite is executable with `./scripts/check.sh`.

| Scenario | Proof |
|---|---|
| parallel specialists | two distinct versioned specialist reports and overlapping start times |
| poisoned/restricted evidence | quarantined source refs and compensation content never enter mission claims |
| checkpoint authority | unauthorized actor receives 403; checkpoint remains pending |
| interruption/resume | same deterministic step IDs and attempts after resume |
| demo write isolation | organizer approval completes the recommendation with zero commands |
| live-source command | `google_calendar` snapshot produces one ETag-bound command and queues only after approval |
| duplicate command | succeeded command delivery is an idempotent no-op |
| active lease | a second delivery cannot execute concurrently |
| stale ETag | provider 412 becomes terminal `stale` |
| bounded retry | retries stop at the configured maximum |
| preference isolation | explicit preference write returns `authority_effect=none`; runtime authorization does not read it |
| credential-shaped event | schema validation rejects it before ingestion |

Evaluation scores final typed results, evidence support, trajectory, policy compliance, idempotency, completion, latency, and cost. It never evaluates or stores hidden reasoning.
