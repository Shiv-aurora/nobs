# Security Model

## Security objective

NoPing should make organizational knowledge easier to reach **without flattening identity, privacy, or decision authority**.

The most important invariant is:

> A model may synthesize evidence, but it may not grant itself access, invent authority, or turn untrusted content into policy.

## Identities

| Identity | Allowed capabilities |
|---|---|
| Mattermost user | normal Mattermost access plus NoPing queries under existing session |
| Mattermost VM service account | invoke private agent Cloud Run; publish normalized work events; write logs/metrics |
| agent service account | call Vertex AI/ADK, Model Armor, Firestore, logs/traces/metrics, read one signing secret |
| Pub/Sub push service account | mint OIDC push tokens and invoke only configured private services |
| budget guard service account | write logs; inspect and stop Compute instances through a custom two-permission role |

No runtime service account can create, resize, snapshot, or delete general infrastructure.

## Request authentication

### Mattermost path

1. Mattermost authenticates the user session.
2. Plugin resolves the server-side user and replaces any browser-supplied requester identity.
3. VM gets an ID token for the exact Cloud Run audience from the metadata server.
4. Plugin adds HMAC v1 headers over:

```text
v1
unix_timestamp
UPPER_METHOD
exact_path_and_query
raw_body
```

5. Cloud Run IAM and HMAC middleware must both pass.

Replay window and constant-time signature comparison are enforced. Shared cross-language vectors live in `contracts/signature_vector.json`.

### Pub/Sub path

OIDC validation pins:

- expected audience;
- expected service-account email;
- verified email claim.

Malformed payloads return `400`, unsigned production delivery returns `401`, and duplicate event IDs are no-ops.

## Authorization order

Authorization is performed before retrieval and before Gemini:

```text
intent → requester roles → evidence scope → policy → authority/delegation → model
```

Examples:

- salary/compensation intent from Maya is refused without fetching the HR evidence body;
- Atlas status evidence is available to project participants;
- a launch exception requires `security_approver` or an active, scoped `acting_security_approver` delegation;
- a model cannot convert revenue urgency into permission.

## Prompt injection and tool poisoning

Defense in depth:

1. incoming user prompt is screened;
2. evidence is scanned and quarantined individually;
3. only allowed evidence enters the model context;
4. Google Model Armor screens prompt and final response in production;
5. the response fails closed if the guard is unavailable or blocks it;
6. the audit trace records the finding without logging sensitive evidence bodies.

The seeded malicious document says to ignore instructions, reveal private data, and approve Atlas. It is quarantined while trusted evidence still answers the factual question.

## Decision safety

Authority-bound requests never use a model-generated outcome. NoPing may:

- gather facts;
- identify applicable policy;
- identify the current authorized human;
- create a decision card;
- record that person’s explicit response.

Decision memory includes canonical class, project scope, facts hash, source decision, actor, outcome, rationale, creation, and expiry. A changed facts hash or expired memory forces re-evaluation.

## Privacy and observability

Logs exclude:

- full prompts;
- private messages;
- evidence bodies;
- passwords/tokens;
- raw authorization headers.

Logs retain operational metadata such as run ID, requester ID, intent, status, route hops, evidence count, security finding count, token usage, and latency. Ordinary traces may be sampled; denials, security findings, escalations, failures, and demo runs should be retained.

## Threats explicitly addressed

- browser impersonates another employee;
- public caller reaches Cloud Run;
- replay or body tampering;
- Pub/Sub spoofing;
- prompt injection in query or source;
- retrieval of unauthorized HR data;
- model approves a human-only decision;
- stale delegation grants authority;
- duplicate events create duplicate decisions;
- agent loop/cost explosion;
- business runtime can stop or resize infrastructure;
- secrets accidentally enter Git.

## Residual risks requiring Phase 2 validation

- real Mattermost version/plugin API compatibility;
- actual Google IAM and Model Armor responses;
- connector OAuth scopes and webhook signature validation;
- evidence permission synchronization from production systems;
- organization-specific data retention and legal requirements;
- TLS/domain configuration if the demo uses a hostname rather than raw-IP HTTP.
