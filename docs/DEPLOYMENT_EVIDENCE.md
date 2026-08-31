# Sanitized deployment evidence

Updated 2026-08-30. This file contains identifiers and hashes only; no tokens, credentials, private evidence, or passwords.

## Project and artifacts

| Evidence | Value |
|---|---|
| project | `noping-agentic-shiv-2026` |
| active deploy account | `shivamarora.sa05@gmail.com` |
| region | `us-central1` (`global` for Gemini/Agent Registry where required) |
| repository | `us-central1-docker.pkg.dev/noping-agentic-shiv-2026/noping-containers` |
| agent image | `agent-service:submission-polish-20260830` → `sha256:e2e9b30ce8f2c460763bd4a9e36cf0f22f73586be9075ef1a2e12a50236842fe` |
| executor image | active immutable digest `sha256:fd5d451af0f1a5e4b5e449f96ba189ed21b42884c9fd824160ad0e68c5002b15` |
| workspace image | `noping-mattermost:submission-polish-20260830` → `sha256:949c568a5f291b4a281648791434e2abc449654fa55eac4dfb72d4c8bc947bcf` |

## Google agent platform

| Evidence | Value |
|---|---|
| primary model | Vertex AI `gemini-3.5-flash` |
| real model proof | four typed ADK calls completed; specialist calls overlapped |
| Model Armor | `projects/noping-agentic-shiv-2026/locations/us-central1/templates/noping-enterprise-guard`, fail closed |
| Agent Engine | `projects/206425724068/locations/us-central1/reasoningEngines/1977754786799288320` |
| Agent Registry | four `global` services: controller, Work Graph, Policy Evidence, resolution synthesizer |
| Agent Gateway | not deployed; no A2A/MCP hop on the critical path |

## Deployed services

| Service | Private revision / bound |
|---|---|
| `noping-agent-service` | `noping-agent-service-00018-4bs`; max 1, concurrency 4, private, 100% traffic |
| `noping-action-executor` | `noping-action-executor-00002-4sq`; max 1, concurrency 1, private |
| `noping-budget-guard` | `noping-budget-guard-00008-992`; max 1, concurrency 1 |
| `noping-mattermost` VM | `e2-small`, static IP `35.202.201.122`, healthy image `nobs-release:submission-polish-20260830` |
| judging uptime | daily shutdown timer removed and disabled in instance startup metadata; separate 90% budget guard retained |
| Firestore | Native `(default)`, `us-central1` |
| Pub/Sub | work events + DLQ; action commands + DLQ; budget updates |

## IAM and command path

- `noping-action-executor` has only `roles/cloudtrace.agent`, `roles/datastore.user`, `roles/logging.logWriter`, `roles/monitoring.metricWriter`, and `roles/telemetry.tracesWriter` at project scope.
- The executor is the only `roles/secretmanager.secretAccessor` member on `noping-google-calendar-credentials`.
- `noping-agent` has `roles/pubsub.publisher` on `noping-action-commands`.
- `noping-pubsub-push` is the only Cloud Run invoker on the executor.
- `noping-action-commands-push` uses OIDC audience matching the executor URL, 60-second ack deadline, 10–300 second retry backoff, five delivery attempts, and `noping-action-commands-dlq`.
- No `allUsers` or `allAuthenticatedUsers` binding exists on either private Cloud Run service.

## Production mission proof

The signed-in deployed UI started `mission-4bc9ce53ece5` on revision `00016-bhd`. Cloud Logging records four `gemini-3.5-flash` calls, parallel Work Graph and Policy Evidence specialist spans, and final status `waiting_human`. Firestore contains all seven deterministic mission-step IDs plus checkpoint `checkpoint-a53f0dca9b4b`; the demo-source mission contains zero commands. Trace `c5669373c4d2916f8c6ae33162d6e1bf` correlates the persisted mission.

All four native Agent Registry services now use their versioned `/v1/executable-agents/<service-id>` endpoints. The `NoPing $25 guardrail` remains USD 25 with 25/50/75/90/100% thresholds, and `noping-budget-guard-00008-992` remains ready.

No external Calendar mutation was performed merely to manufacture evidence. No `allUsers` access, budget increase, budget-guard removal, data deletion, or credential output occurred.

## Submission-polish browser proof

The deployed Workrooms route returned `Workrooms - NoBS` and showed 101 auditable updates. Each real-work card showed 20–21 updates and three recent activity previews; the live activity rail showed ten entries. DOM verification found the static NoBS wordmark, no product-switch button or menu, and zero visible `Mattermost` strings. The idempotent production seed completed against the HTTPS endpoint using a trusted CA bundle.
