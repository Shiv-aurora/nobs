# Agent Service API

All production plugin calls require Cloud Run IAM plus NoPing HMAC. Pub/Sub uses pinned OIDC. Demo mode permits local unsigned calls.

## Health

`GET /healthz`

Returns mode, AI state, and version.

## Bootstrap

`GET /v1/bootstrap?user_id=maya`

Returns current user, projects, pending Needs You decisions, semantic work states, and attention metrics.

## Query

`POST /v1/query`

```json
{
  "requester_id": "maya",
  "text": "Why is Atlas blocked?",
  "team_id": "support",
  "context": {}
}
```

Result includes intent, status, answer, route steps, authorized evidence, confidence, freshness, people interrupted, decision linkage, policy result, security findings, cache state, and model usage.

## Run

`GET /v1/runs/{run_id}`

Reads a prior query result.

## Decisions

- `GET /v1/decisions?assignee_id=alex`
- `POST /v1/decisions/{decision_id}/resolve`

```json
{
  "actor_id": "alex",
  "status": "rejected",
  "rationale": "SEC-184 must complete before launch."
}
```

Resolution performs a deterministic authority check and creates scoped decision memory.

## Registry and audit

- `GET /v1/registry`
- `GET /v1/audit?limit=50`
- `GET /v1/metrics`

## Work events

### Direct signed ingestion

`POST /v1/events`

### Authenticated Pub/Sub push

`POST /v1/events/pubsub`

Payload data decodes to the normalized `WorkEvent` contract. Duplicate event IDs return accepted false without duplicating state.

## Demo reset

`POST /v1/demo/reset`

Available only when `NOPING_DEMO_MODE=true`.

## Error behavior

- `400` malformed event/payload;
- `401` missing or invalid service signature/OIDC;
- `403` disabled demo reset or unauthorized action;
- `404` unknown user/run/decision;
- `409` decision already resolved;
- `429` bounded user/org/concurrency admission;
- safe structured result for model budget, guard, or provider failure where appropriate.
