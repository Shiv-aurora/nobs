# Implementation and deployment status

Updated 2026-08-30 in project `noping-agentic-shiv-2026`, branch `main`.

## Verified baseline

| Item | Verified state |
|---|---|
| active account | `shivamarora.sa05@gmail.com` |
| billing / budget | billing enabled; project-filtered **NoPing $25 guardrail** retained with 25/50/75/90/100% thresholds |
| collaboration | `noping-mattermost` `e2-small` VM at `35.202.201.122`; Mattermost/PostgreSQL/Caddy |
| gateway | private Cloud Run `noping-agent-service`, baseline revision `00011-2zb`, max 1 / concurrency 4 |
| budget guard | private Cloud Run `noping-budget-guard`, revision `00008-992`; armed independently |
| primary model | production and real probe: `gemini-3.5-flash` in Vertex AI `global` |
| durable state | Firestore Native `(default)`, `us-central1` |
| model safety | Model Armor template `noping-enterprise-guard`, `us-central1`, fail closed |
| agent lifecycle | Agent Registry API enabled; four native service entries registered |
| agent context | Agent Engine `1977754786799288320`, `us-central1`, for Sessions and preference Memory Bank |
| events | `noping-work-events` plus DLQ and OIDC push subscription |
| images built | agent/executor tag `59aadc4`: `sha256:9bdb117…` / `sha256:589980…`; Mattermost tag `22fe77e`: `sha256:4b818c…` |

All Cloud Run services in the verified baseline are private; no `allUsers` invocation binding is permitted.

## Implemented in source

- qualifying Gemini 3.5 defaults throughout code, Compose, Terraform, and examples;
- `DelegateDirectory` separated from the versioned Executable Agent Registry;
- typed ADK mission controller, real parallel Work Graph and Policy Evidence agents, deterministic critic/authority gate, and typed resolution agent;
- no fixture-selected final meeting results, prewritten execution transcripts, or fixed fake timings;
- Firestore mission, step, checkpoint, command, attempt, manifest, and counter persistence;
- resume that skips completed deterministic step IDs;
- Model Armor on every ADK prompt and response, plus permission-filtered/quarantined evidence;
- explicit preference-only Memory Bank adapter that mission authorization never reads;
- organizer checkpoint with demo/write isolation;
- separate idempotent Calendar executor with transactional leases, ETag preconditions, bounded retries, post-write verification, and hashed responses;
- body-free structured logs and OpenTelemetry spans for mission nodes and executor actions;
- plugin no longer executes Calendar writes directly.

## Real model/runtime proof

A bounded live production-path mission used real Vertex AI credentials and completed with:

- model: `gemini-3.5-flash`;
- native registry discovery: `google_agent_registry`;
- Agent Engine Sessions enabled;
- four ADK model calls;
- controller: 8,223.437 ms;
- Work Graph specialist: 7,416.848 ms;
- Policy Evidence specialist: 6,007.249 ms;
- synthesizer: 6,562.838 ms;
- deterministic critic: 0.075 ms;
- deterministic authority gate: 0.077 ms.

The specialists shared a start boundary and overlapped; these are measured durations, not fixture values. The proof used local `NullStateStore` to avoid polluting production Firestore; the deployed service uses Firestore.

## Validation

`./scripts/check.sh` passes: 87 agent-runtime tests, 8 budget-guard tests, 6 action-executor tests, all Go packages, strict TypeScript, Python compilation, shell/static checks, credential scan, and Git whitespace. Terraform 1.x with Google provider 8.0.0 validates successfully.

## Deployment progress

| Component | State |
|---|---|
| Agent Registry services | deployed |
| Agent Engine Sessions/Memory resource | deployed |
| tested source commits | `4a65f61`, `22fe77e`, `59aadc4` |
| immutable images | pushed |
| agent/executor/Mattermost revisions | pending final rollout |
| executor SA, Calendar-secret grant, command topics | blocked pending explicit user approval of the production IAM blast radius |
| production signed/browser mission proof | pending that rollout |
| final docs/diagram | in progress; must be reconciled with final deployed revisions |

No production data was deleted, no public service was created, the budget was not changed, and the budget guard was not removed.
