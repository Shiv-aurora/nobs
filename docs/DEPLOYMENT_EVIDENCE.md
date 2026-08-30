# Sanitized deployment evidence

Updated 2026-08-30. This file contains identifiers and hashes only; no tokens, credentials, private evidence, or passwords.

## Project and artifacts

| Evidence | Value |
|---|---|
| project | `noping-agentic-shiv-2026` |
| active deploy account | `shivamarora.sa05@gmail.com` |
| region | `us-central1` (`global` for Gemini/Agent Registry where required) |
| repository | `us-central1-docker.pkg.dev/noping-agentic-shiv-2026/noping-containers` |
| agent image | `agent-service:4bee667` → `sha256:7f1a18d2963d3c10a5346ad544fa390e8950025577407af46fa6d4e9021032c7` |
| executor image | `action-executor:59aadc4` → `sha256:58998091fe6c739c66d1e43045daf4b8552e59c3b1f6631c3d681f07b5556ed4` |
| Mattermost image | `noping-mattermost:22fe77e` → `sha256:4b818c621df9be37ba86e1d123e68e7883af9a467a1b5248560170e37ab3af9f` |

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
| `noping-agent-service` | `noping-agent-service-00016-bhd`; max 1, concurrency 4, private |
| `noping-action-executor` | `noping-action-executor-00001-8rb`; max 1, concurrency 1, private |
| `noping-budget-guard` | `noping-budget-guard-00008-992`; max 1, concurrency 1 |
| `noping-mattermost` VM | `e2-small`, static IP `35.202.201.122`, healthy image `nobs-release:22fe77e` |
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
