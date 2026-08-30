# Implementation and deployment status

Updated 2026-08-30 in project `noping-agentic-shiv-2026`, branch `main`.

## Verified baseline

| Item | Verified state |
|---|---|
| active account | `shivamarora.sa05@gmail.com` |
| billing / budget | billing enabled; project-filtered **NoPing $25 guardrail** retained with 25/50/75/90/100% thresholds |
| collaboration | `noping-mattermost` `e2-small` VM at `35.202.201.122`; Mattermost/PostgreSQL/Caddy |
| gateway | private Cloud Run `noping-agent-service`, revision `00016-bhd`, max 1 / concurrency 4 |
| action executor | private Cloud Run `noping-action-executor`, revision `00001-8rb`, max 1 / concurrency 1 |
| budget guard | private Cloud Run `noping-budget-guard`, revision `00008-992`; armed independently |
| primary model | production and real probe: `gemini-3.5-flash` in Vertex AI `global` |
| durable state | Firestore Native `(default)`, `us-central1` |
| model safety | Model Armor template `noping-enterprise-guard`, `us-central1`, fail closed |
| agent lifecycle | Agent Registry API enabled; four native service entries registered |
| agent context | Agent Engine `1977754786799288320`, `us-central1`, for Sessions and preference Memory Bank |
| events | work events plus DLQ; action commands plus DLQ and authenticated OIDC push |
| images deployed | agent `4bee667` → `sha256:7f1a18d…`; executor `59aadc4` → `sha256:589980…`; Mattermost `22fe77e` → `sha256:4b818c…` |

All Cloud Run services in the verified baseline are private; no `allUsers` invocation binding is permitted.

## Implemented in source

- qualifying Gemini 3.5 defaults throughout code, Compose, Terraform, and examples;
- `DelegateDirectory` separated from the versioned Executable Agent Registry;
- typed ADK mission controller, real parallel Work Graph and Policy Evidence agents, deterministic critic/business/Calendar gates, and typed resolution agent;
- no fixture-selected final meeting results, prewritten execution transcripts, or fixed fake timings;
- Firestore mission, step, checkpoint, command, attempt, manifest, and counter persistence;
- resume that skips completed deterministic step IDs;
- Model Armor on every ADK prompt and response, plus permission-filtered/quarantined evidence;
- explicit preference-only Memory Bank adapter that mission authorization never reads;
- separate business-authority and organizer-only Calendar checkpoints with demo/write isolation;
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

A second proof ran through the deployed Mattermost UI and private Cloud Run gateway on revision `00016-bhd`. Mission `mission-4bc9ce53ece5` completed four real `gemini-3.5-flash` ADK calls and persisted the access gate, controller, both parallel specialists, evidence critic, synthesizer, and authority gate. Firestore records status `waiting_human`, checkpoint `checkpoint-a53f0dca9b4b`, and trace `c5669373c4d2916f8c6ae33162d6e1bf`. Because the meeting source is `demo`, the mission created zero external commands.

## Validation

`./scripts/check.sh` passes: 92 agent-runtime tests, 8 budget-guard tests, 7 action-executor tests, all Go packages, strict TypeScript, Python compilation, shell/static checks, credential scan, and Git whitespace. Terraform 1.x with Google provider 8.0.0 validates successfully.

## Deployment progress

| Component | State |
|---|---|
| Agent Registry services | deployed |
| Agent Engine Sessions/Memory resource | deployed |
| tested source commits | `4a65f61`, `22fe77e`, `59aadc4`, `4bee667` |
| immutable images | pushed and deployed by digest |
| agent/executor/Mattermost revisions | deployed and healthy |
| executor SA and Calendar-secret grant | deployed; executor is the sole accessor on the Calendar secret |
| command topic / DLQ / push | deployed; agent publishes, Pub/Sub OIDC invokes executor |
| production browser mission proof | passed on `mission-4bc9ce53ece5` |
| final docs/diagram | reconciled with deployed revisions |

No production data was deleted, no public Cloud Run service was created, the budget was not increased, and the budget guard was not removed. The existing **NoPing $25 guardrail** remains active.
