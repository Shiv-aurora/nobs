# Data and state model

Firestore owns distributed mission state under `organizations/{organization_id}`. Mattermost/PostgreSQL and connected providers retain authoritative source content.

## Firestore collections

| Collection | Purpose | Important consistency rule |
|---|---|---|
| `missions` | mission status, model/workflow version, meeting/ETag, recommendation, trace | transitions persist with step updates |
| `mission_steps` | deterministic node ID, kind, agent/version, attempt, times, refs, failure | completed step ID is not rerun on resume |
| `human_checkpoints` | gate type, authority type, authorized actors, command IDs, decision, rationale, times | business and Calendar approvals are distinct pending → approved/rejected events |
| `commands` | typed approved intent, idempotency key, ETag, lease, terminal result | executor claims transactionally |
| `command_attempts` | immutable deterministic attempt ID and safe outcome metadata | duplicate create is an idempotent no-op |
| `agent_manifests` | stable ID/version, schemas, scopes, tools, identity, health | routing selects approved active versions only |
| `work_events` | normalized bounded envelope and source version | stable source event ID suppresses duplicates |
| `work_state` | compact semantic projection | source time/version prevents stale overwrite |
| `decisions` / `decision_memory` | authority-bound outcomes and reusable confirmed memory | reuse requires matching facts/scope/policy/expiry |
| `audit_events` | safe actor/entity/outcome metadata | no raw secrets, prompts, or private bodies |
| `usage_counters` | rate/model token admission | reserve before provider call |

Existing product collections for meetings, delegations, handoffs, sessions, OOO, and query results remain tenant-scoped. Legacy pre-mission meeting runs are retained for audit history but never presented as current executable-agent output.

## Mission schema

`MissionRun` includes stable mission ID, meeting ID/ETag, trigger, actor, status/current stage, typed plan, specialist reports, critic report, authority-typed agenda resolutions, recommendation, proposed commands, separate business/Calendar checkpoint IDs, evidence counts, trace ID, timestamps, and failure code.

`MissionStep` includes stable step ID, ordinal, node ID/kind, agent ID/version where applicable, status, attempt, input/output references, timestamps, measured duration, and failure code. No hidden reasoning is stored.

`EvidenceClaim` includes a generated claim ID, statement, exact source reference, observed timestamp, and bounded confidence. Specialists may cite only the source map they were given; the critic retains accepted claim IDs and conflicts.

## Command schema

`ProposedCommand` includes command/action type, target reference, expected ETag, bounded payload, status, deterministic idempotency key, mission/business-checkpoint/Calendar-checkpoint/trace IDs, requester/organizer and approval time, attempt/lease state, applied ETag, provider response hash, and failure code.

Only live `google_calendar` projections may produce Calendar commands. Demo fixture records remain useful input data but are not external write targets.

## State ownership

- Mattermost/PostgreSQL: users, sessions, memberships, channels, posts, threads, files, realtime delivery.
- Google Calendar/GitHub/other provider: source facts and resource versions.
- Firestore: compact projections, durable workflow and governance state.
- Vertex Sessions: ADK session events only.
- Vertex Memory Bank: explicit non-authoritative preferences only.
- process memory: tests, static seed/configuration, and bounded cache only.

All production timestamps use real UTC-derived wall time. The fixed demo timestamp is injected only by deterministic tests.
