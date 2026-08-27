# NoPing Implementation

## Build strategy

NoPing is implemented as a mature collaboration substrate plus a distinct agent runtime:

1. **Mattermost distribution layer** — official Mattermost Team Edition image and PostgreSQL.
2. **NoPing plugin** — Go server proxy/security boundary and full React/TypeScript product route.
3. **NoPing agent service** — FastAPI orchestration, routing, policy, evidence, work-state, decisions, memory, and audit.
4. **Google Cloud production layer** — private Cloud Run, Gemini through Google ADK, Firestore, Pub/Sub, Model Armor, Secret Manager, observability, and bounded Compute Engine.

This avoids a toy rewrite while keeping NoPing’s original contribution isolated and reviewable.

## Component boundaries

### Mattermost plugin server

Responsibilities:

- trust the authenticated Mattermost session—not browser-supplied identity;
- translate opaque Mattermost IDs to stable organizational usernames;
- expose a narrow `/plugins/com.noping.enterprise/api/v1/*` proxy surface;
- generate a Google-signed identity token for private Cloud Run from Compute metadata;
- sign the exact method, path/query, timestamp, and body with HMAC v1;
- publish Mattermost WebSocket notifications for run and decision changes;
- never hold model credentials.

### React/TypeScript product

Routes:

- Home / Ask Your Company
- Needs You
- Projects
- Teams
- People
- Registry
- Audit
- System
- Rooms fallback

The UI renders structured answers, route traces, evidence, freshness, decision cards, work state, and attention metrics. It is not an embedded assistant sidebar.

### Agent service

Core execution order:

1. service identity + HMAC verification;
2. user/org rate admission;
3. prompt safety guard;
4. deterministic intent classification;
5. restricted-intent and permission policy;
6. organization routing;
7. authorized evidence retrieval;
8. poisoned-evidence quarantine;
9. scoped decision-memory lookup;
10. authority resolution / OOO delegation;
11. AI budget reservation;
12. Gemini synthesis through Google ADK when needed;
13. Model Armor response screening;
14. result persistence, audit, metrics, and notification.

The service deliberately does not call Gemini for permission denials, registry reads, existing decisions, health checks, or deterministic policy outcomes.

## Logical delegate model

Delegate kinds:

- `personal` — employee knowledge and authority boundary;
- `project` — project relationships, blockers, evidence, and decisions;
- `team` — department purpose, membership, and approved shared context;
- `policy` — deterministic policy representation;
- `router` — entity discovery and route planning;
- `authority` — escalation and delegation validation.

Delegates share a model provider but not identity, scopes, or authority. Registry records are discoverable and auditable.

## Semantic work state

External activity is normalized to one `WorkEvent` contract:

```json
{
  "id": "event-pr-892-reviewed",
  "source": "github",
  "event_type": "pull_request.reviewed",
  "actor_user_id": "daniel",
  "entity_ids": ["atlas", "auth-392"],
  "occurred_at": "2026-08-27T13:20:00-04:00",
  "payload": {"number": 892, "review_state": "approved"}
}
```

An event-driven projector converts normalized events and organization relationships into compact person/project states. The projector is tool-neutral; GitHub, Calendar, Jira, and Mattermost adapters only normalize their source payloads.

## Persistence

`StateStore` is a defined adapter boundary:

- in-memory/recording implementations for tests;
- Firestore implementation for decisions, memories, audit, events, statistics, and query results;
- Mattermost/PostgreSQL remains the source for collaboration records and large evidence bodies.

NoPing stores compact semantic state and references rather than copying complete message histories into Firestore.

## Security controls

- private Cloud Run IAM—no `allUsers` or `allAuthenticatedUsers`;
- Compute service account identity token + exact-request HMAC;
- Pub/Sub OIDC audience and service-account pinning;
- deterministic authorization before evidence retrieval;
- restricted data never enters the model context;
- local poisoned-evidence scanner plus Model Armor prompt/response screening;
- fail-closed behavior on guard or model ambiguity;
- least-privilege service accounts;
- redacted structured logs and optional OTLP traces;
- independent budget guard that cannot access business data or create infrastructure.

## Cost controls

The implementation enforces limits at four layers:

1. Terraform resource bounds;
2. Cloud Run `min=0`, `max=1`, concurrency and memory/CPU caps;
3. application request/model/token counters with pre-reservation;
4. Cloud Billing alerts and an independently permissioned 90% VM shutdown guard.

The budget guard begins in dry-run and requires typing `ARM` after its synthetic notification is inspected.

## Phase 1 completion boundary

Built in the sandbox:

- Mattermost plugin source and product UI;
- deterministic agent runtime and tests;
- Google ADK, Firestore, Pub/Sub, Model Armor, identity-token, and telemetry adapters;
- local and Google Cloud deployment source;
- budget guard and cost constraints;
- CI/static validation/security scans;
- demo fixtures, screenshots, docs, and exact Phase 2 handoff.

Not honestly executable without laptop credentials/network:

- full npm and Go dependency installation/package lock generation;
- Docker Mattermost runtime;
- Terraform provider initialization and Google Cloud apply;
- real Gemini/ADK call;
- real Model Armor template call;
- real GitHub and Calendar OAuth/webhooks;
- remote GitHub push and Devpost submission.

## Phase 2 contract

Codex must preserve the architecture and complete only credential/runtime-dependent work. It may fix provider/API mismatches found by real validation, but must not replace Mattermost with a static frontend, make Cloud Run public, remove policy checks, disable Model Armor, raise limits, introduce non-Google production hosting, or exceed the `$25` budget boundary without explicit approval.

See [`docs/CODEX_HANDOFF.md`](docs/CODEX_HANDOFF.md).
