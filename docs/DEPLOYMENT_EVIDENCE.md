# Sanitized deployment evidence

Updated 2026-08-30. This file contains identifiers and hashes only; no tokens, credentials, private evidence, or passwords.

## Project and artifacts

| Evidence | Value |
|---|---|
| project | `noping-agentic-shiv-2026` |
| active deploy account | `shivamarora.sa05@gmail.com` |
| region | `us-central1` (`global` for Gemini/Agent Registry where required) |
| repository | `us-central1-docker.pkg.dev/noping-agentic-shiv-2026/noping-containers` |
| agent image | `agent-service:59aadc4` → `sha256:9bdb11725cf9318b8e18092f1acb3d8af27e9c9a279d38c60abeb0796c905620` |
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

## Baseline deployed services

| Service | Private revision / bound |
|---|---|
| `noping-agent-service` | baseline `noping-agent-service-00011-2zb`; max 1, concurrency 4 |
| `noping-budget-guard` | `noping-budget-guard-00008-992`; max 1, concurrency 1 |
| `noping-mattermost` VM | `e2-small`, static IP `35.202.201.122` |
| Firestore | Native `(default)`, `us-central1` |
| Pub/Sub | work events + DLQ; budget updates |

## Rollout evidence pending approval

The final agent/executor/Mattermost revisions, executor IAM bindings, command topics/subscription, Firestore mission documents, private IAM audit, trace query, signed smoke, browser run, and final budget verification will be added only after the explicitly requested executor-secret/IAM approval is received and the rollout completes.

No `allUsers` access, budget increase, budget-guard removal, data deletion, or credential output is part of this rollout.
