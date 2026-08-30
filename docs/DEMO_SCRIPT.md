# Four-minute architecture proof

Use one continuous screen recording. Show persisted/runtime evidence; do not narrate unavailable services or perform a real Calendar write without the dedicated demo organizer’s approval.

## 0:00–0:20 — Problem and result

Open Project Atlas in NoBS.

> “Workplace chat made everyone reachable—and every routine question an interruption. NoBS lets agents complete coordination while identity, evidence permissions, and human authority stay intact.”

State the two proof outcomes: a routine engineering sync can return 30 minutes; launch readiness can retain only 15 minutes for one human security decision.

## 0:20–0:50 — Create one durable mission

Open Calendar and prepare **Atlas launch readiness**. Show the returned mission ID/status, then the corresponding Firestore mission/step records or authenticated mission endpoint.

> “This is not a fixture timeline. The meeting snapshot creates one Firestore-authoritative mission using the current Calendar ETag and real UTC time.”

## 0:50–1:25 — Actual parallel agents

Show the mission execution view or Cloud Trace. Point to:

- controller on `gemini-3.5-flash`;
- Work Graph and Policy Evidence agent IDs/version `1.0.0`;
- overlapping measured timings;
- source references and accepted claim IDs;
- deterministic critic after fan-out.

> “Employee and project delegates are logical scope records. These two specialists are actual typed ADK executions running concurrently.”

## 1:25–1:50 — Evidence security

Show the poisoned vendor evidence security finding and absence from specialist claims.

> “Permission filtering and the local source scanner act before context. Model Armor screens every ADK input and output and fails closed. The model cannot cite a source it was not given.”

## 1:50–2:15 — Resolution and authority

Show resolved engineering/customer context, one authority-bound security item, and the 60 → 15 minute recommendation. Open the persisted pending checkpoint with the exact organizer.

> “Gemini locates and synthesizes evidence. Deterministic policy decides that a human is required, persists the checkpoint, and pauses the same mission.”

## 2:15–2:40 — Approval and executor

If using seeded demo data, approve and show **Approved recommendation · demo data unchanged**, then show zero commands.

For a dedicated live demo Calendar event only, approve as organizer and show:

- one ETag-bound command in Firestore;
- Pub/Sub command ID delivery;
- private executor service account;
- lease/idempotency state;
- `If-Match` and verified result metadata (never the credential/body).

> “The model and gateway do not hold the Calendar credential. Only this private executor can apply an approved command.”

## 2:40–3:00 — Failure safety

Run or show the duplicate/stale evaluation output: duplicate delivery is a no-op, active lease prevents concurrent execution, and a stale ETag becomes terminal `stale`. Also show resume keeping the same step IDs/attempts.

## 3:00–3:35 — Architecture

Open `docs/architecture.png` full-screen. Trace the four trust boundaries: collaboration, private read-only gateway, durable bounded mission, isolated write executor. Point to Firestore, Agent Registry, Sessions, preference-only Memory Bank, Model Armor, Pub/Sub/DLQs, traces, identities, and $25 guard.

> “NoBS uses agents only for open-ended knowledge work. Deterministic nodes own access, validation, authority, idempotency, and side effects. That gives us enterprise autonomy without an unrestricted swarm or unnecessary microservices.”

## 3:35–4:00 — Google Cloud proof

Show sanitized commands/pages for:

- project and private Cloud Run revisions;
- `gemini-3.5-flash` log/trace metadata;
- four Agent Registry services;
- Agent Engine resource;
- Firestore collections and Pub/Sub topics/DLQs;
- Model Armor template;
- dedicated service accounts and absence of `allUsers`;
- $25 budget and independent guard.

End on measured values only: agenda items resolved, human checkpoints created, minutes returned, injected sources blocked, model calls/tokens, duplicate effects prevented, and completed mission latency.
