# Security and authority model

NoBS makes organizational knowledge easier to reach without flattening identity, evidence permissions, or decision authority.

## Control order

`identity → tenant → requester role → entity scope → evidence authorization → policy → delegation → model execution → business authority → Calendar authority → external action`

All controls through delegation are deterministic and occur before Gemini receives evidence. Models cannot grant access, choose an approving actor, waive a policy, resolve an authority checkpoint, or execute a command.

## Trust boundaries

1. **Browser:** untrusted. The Go plugin discards browser-supplied requester identity and resolves the Mattermost session user server-side.
2. **Mattermost/plugin:** collaboration authority. It invokes the private gateway using both a Google IAM identity token and an HMAC over method, exact path/query, timestamp, and body.
3. **Gateway/mission runtime:** read-only enterprise-agent boundary. It applies replay, tenant, rate, concurrency, model-budget, evidence, policy, and Model Armor controls. It lacks the Calendar credential.
4. **Firestore/Pub/Sub:** durable at-least-once control plane. Tenant-scoped transactions own mission/checkpoint/command state; push uses a pinned service account and audience.
5. **Action executor:** isolated write boundary. It has no model/query tools and reads only the Calendar credential plus approved command state.
6. **Local Meet bridge:** demo-only media boundary. It receives one validated Meet URI, one leased session, and one rotating live nonce. It has no Calendar credential, evidence-query role, business authority, or command approval capability.

## Evidence security

- Retrieval receives trusted organization/requester context from the runtime, never the model.
- Source results are permission-filtered, bounded, and represented by IDs, timestamps, confidence, security state, and hashes.
- Local poisoning detection excludes quarantined sources before agent context.
- Production Model Armor screens each ADK prompt and response and fails closed when unavailable.
- The deterministic critic accepts only citations to the exact supplied source map and removes missing, low-confidence, conflicting, or unauthorized claims.
- Logs and traces contain operational metadata, never prompts, cookies, OAuth tokens, raw message bodies, hidden reasoning, or poisoned payloads.

## Human authority and commands

An authority-bound agenda item persists a business checkpoint whose actor is resolved by the deterministic `PolicyEngine`; for the Atlas security flow that is Sarah or Alex only while Sarah's delegation is valid. The meeting organizer receives no business authority merely by organizing. Business approval resumes the same mission and creates a distinct organizer-only Calendar checkpoint. Demo sources may record both events but cannot produce a command. A live Calendar source produces one typed command containing target, expected ETag, payload, both checkpoint IDs, trace ID, organizer, and deterministic idempotency key.

The executor reloads the command and both persisted approvals, verifies their distinct actors and command binding, claims a lease, uses Calendar `If-Match`, reads the result, and stores only a response hash and safe metadata. Duplicate/terminal/leased commands are no-ops. HTTP 412 becomes terminal `stale`.

## Identity matrix

| Identity | Narrow grants |
|---|---|
| Mattermost VM | invoke gateway; publish normalized work events; logging/metrics |
| agent runtime | Vertex AI, Model Armor, Agent Registry read, Firestore state, traces/logs, publish one command topic |
| Pub/Sub push | mint OIDC for configured private endpoints |
| action executor | Firestore, traces/logs, read one Calendar secret |
| local Meet bridge | claim/status endpoints and one ephemeral live-session nonce; no cloud IAM role in the deployed baseline |
| budget guard | logging plus custom `compute.instances.get/stop` for the configured VM |

No runtime identity receives Owner or Editor. Cloud Run remains private; no `allUsers` binding is allowed.

## Memory boundaries

Confirmed decision memory is authoritative only when scope, facts hash, policy version, actor authority, outcome, freshness, and expiry still match. Preference Memory Bank accepts only explicit allowlisted personalization and is tagged `authority_effect=false`; no authorization code reads it.

## Threat-to-control map

| Threat | Control |
|---|---|
| forged browser identity | server-side Mattermost session resolution |
| replay/tampering | IAM + exact-body HMAC + timestamp window |
| cross-tenant/evidence leak | deterministic scope and permission filtering before context |
| prompt-injected connector content | quarantine + Model Armor + citation allowlist |
| organizer gains business authority | separate deterministic business and Calendar gates |
| model self-approval | deterministic authority gates + durable actor-bound checkpoints |
| direct model side effect | no write tool/credential; separate executor |
| stale or duplicate action | ETag, idempotency key, lease, terminal states, postcondition read |
| secret/log leakage | Secret Manager, structured redacted logs, body-free traces |
| forged or stale Meet worker | separate bridge token, normal service signature, one-owner lease, rotating media nonce, validated `meet.google.com` host |
| overspend | per-query/day admission, max instances, $25 budget, independent VM-stop guard |
