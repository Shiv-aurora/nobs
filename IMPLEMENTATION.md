# NoBS implementation

## Runtime boundaries

1. **Collaboration:** pinned Mattermost 11.10.1 web client/server, PostgreSQL, Caddy, NoBS Go plugin, and React product surfaces.
2. **Private gateway/runtime:** FastAPI on Cloud Run performs IAM/HMAC/replay checks, access/admission, Model Armor, Less Ping, and durable meeting missions. It is read-only with respect to Calendar.
3. **Durable control plane:** Firestore owns mission/checkpoint/command state; Pub/Sub carries normalized work events and command IDs with DLQs; Agent Registry/typed manifests own lifecycle; Agent Engine Sessions and preference Memory Bank have narrow roles.
4. **Private action executor:** separate Cloud Run identity, one Calendar secret, transactional lease/idempotency, `If-Match`, postcondition read, immutable attempt.

## Governed meeting graph

`AccessGate → MissionControllerAgent → [WorkGraphAgent || PolicyEvidenceAgent] → EvidenceCritic → MeetingResolutionAgent → AuthorityGate → HumanCheckpoint? → CommandBuilder → ActionExecutor → ResultVerifier`

The four model nodes are typed Google ADK `LlmAgent` calls on `gemini-3.5-flash`; both specialists use `asyncio.gather` and independent reports. Critic, authority, command, and verification logic is deterministic. Routing permits only approved versioned registry IDs.

Each successful node persists a deterministic step ID, attempt, measured timing, agent ID/version, and output references. Recovery loads Firestore and skips completed nodes. Production uses wall-clock time; deterministic test mode uses an injected fixture clock and executable programs that derive results from source fixtures.

## Less Ping

The existing path remains intentionally lighter: deterministic scope/delegate resolution, permission-aware retrieval, poisoned-source exclusion, one bounded synthesizer, Model Armor, and a native Mattermost thread reply. The UI says delegates/scopes consulted rather than pretending each logical delegate executed an LLM.

## Typed contracts

- `AgentManifest`: ID/version/owner/revision/model/schemas/capabilities/tools/scopes/identity/health/approval/timestamps.
- `MissionRun` and `MissionStep`: durable graph state and safe trace-linked trajectory.
- `EvidenceClaim`, `SpecialistReport`, `CriticReport`, `AgendaResolution`, `MissionRecommendation`: schema-validated evidence and outcome.
- `HumanCheckpoint`: exact authorized actors and one-time durable resolution.
- `ProposedCommand` / `CommandAttempt`: target, ETag, idempotency, trace, lease, outcome hash.
- `WorkEvent`: schema version, stable IDs, correlation/trace, classification, bounded payload, credential-key rejection.

## State and memory

Mattermost/PostgreSQL and external providers own source facts. Firestore stores compact projections/references and all distributed workflow authority. Vertex Sessions stores ADK events only. Memory Bank accepts explicit allowlisted preferences and is never read by authorization. Confirmed decision memory remains scope/facts/policy/actor/expiry-bound in Firestore.

## Security and observability

The plugin resolves the authenticated Mattermost user server-side and signs exact private Cloud Run requests. Pub/Sub push uses OIDC. Model Armor and local scanning protect inputs/evidence/outputs. Logs are structured and redacted. OpenTelemetry spans cover the controller, specialists, critic, synthesizer, authority gate, HTTP requests, and executor commands without bodies or hidden reasoning.

## Cost controls

Cloud Run scales from zero to one. Gateway concurrency is four; executor concurrency is one. A meeting reserves at most four calls, 24k input tokens, and 2.4k output tokens, with daily ceilings. The existing $25 budget and separately permissioned VM-stop guard remain unchanged.

## Verification

`./scripts/check.sh` is the source gate. Current results and production progress are in [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md) and [`docs/STATUS.md`](docs/STATUS.md). Design rationale is in [`docs/ARCHITECTURE_DECISIONS.md`](docs/ARCHITECTURE_DECISIONS.md).
