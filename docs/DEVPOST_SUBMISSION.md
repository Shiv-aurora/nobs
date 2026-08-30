# Devpost submission draft

## Project name

NoBS

## Tagline

Fewer pings. Shorter meetings. More actual work.

## Architecture thesis

**NoBS turns workplace events into durable, governed multi-agent missions. Specialist agents resolve coordination work in parallel, deterministic policy protects access and authority, human judgment pauses and resumes the same mission, and a separate least-privilege executor applies approved actions safely and idempotently.**

## What it does

Workplace chat made everyone reachable—and constantly interruptible. Context already exists across conversations, issues, pull requests, calendars, policies, and prior decisions, but routine questions and status meetings still consume human attention.

NoBS keeps normal Mattermost channels, DMs, threads, files, sessions, permissions, and realtime delivery. For Less Ping, a model-free preflight resolves the responsible logical delegate scope, retrieves only permitted evidence, blocks poisoned sources, and asks one bounded Gemini synthesizer to answer in the native thread. Restricted questions stop before evidence or Gemini; `--direct` stays human-only.

For Less Meeting, NoBS creates one durable mission. A Google ADK controller on Vertex AI `gemini-3.5-flash` assigns two actual specialist agents. Work Graph and Policy Evidence execute concurrently and emit typed, source-cited reports. A deterministic critic removes unsupported/inaccessible claims. A Gemini 3.5 resolution agent classifies each agenda item and recommends cancel, shorten, or keep. Deterministic policy then either completes the mission or persists an actor-bound human checkpoint.

Models cannot self-authorize. Seeded demo meetings can never create external commands. For a real Calendar projection, organizer approval resumes the same mission and persists one ETag-bound typed command. Authenticated Pub/Sub sends only its ID to a separate private executor with no Gemini/query tools. The executor transactionally claims a lease, enforces idempotency and `If-Match`, applies the narrow write, reads the result, and records a hashed verified outcome.

## Why this is more than a chatbot

- Mission state survives process restarts in Firestore; completed nodes are not falsely rerun.
- Actual parallel agent executions have typed schemas, versions, source references, measured timings, usage, and traces.
- Employee/project/team/policy delegates are honestly represented as logical records, not decorated as deployed agents.
- Open-ended evidence synthesis uses agents; identity, authorization, policy, approval, commands, and side effects use deterministic code.
- Google Agent Registry catalogs four executable services; Firestore stores richer governance manifests.
- Vertex Agent Engine Sessions owns ADK context; Memory Bank owns only explicit non-authoritative preferences; confirmed decisions remain policy/facts/authority-bound in Firestore.
- Model Armor fails closed around every ADK call, and permission-aware retrieval/local quarantine keeps unsafe evidence out of context.
- At-least-once delivery is made safe with stable IDs, transactions, leases, ETags, bounded retries, terminal states, and post-write verification—not a false exactly-once claim.

## Google Cloud and Google AI

- Google ADK typed `LlmAgent` programs;
- Vertex AI `gemini-3.5-flash` for the primary judged mission;
- private Cloud Run gateway/runtime and separate executor;
- Firestore Native for missions, steps, checkpoints, commands, attempts, manifests, memory, and audit;
- Pub/Sub work/command topics, OIDC push, retry policy, and DLQs;
- Google Agent Registry with four versioned services;
- Vertex Agent Engine Sessions and preference-only Memory Bank;
- Model Armor fail-closed screening;
- Secret Manager, Artifact Registry, IAM service accounts, Cloud Logging, OpenTelemetry/Trace, Monitoring;
- Compute Engine for the bounded Mattermost demo and the existing $25 project guardrail with a separately permissioned VM-stop service.

Agent code currently executes on private Cloud Run; Agent Engine is used for Sessions/Memory, not claimed as Agent Runtime. Agent Gateway is not deployed because no current critical-path call uses A2A or MCP.

## What we learned

The useful enterprise-agent boundary is neither “one chatbot” nor “one service per employee.” It is a controlled graph of versioned executable programs operating over logical organizational identities. Models are strongest at bounded evidence interpretation; deterministic code is essential wherever an invariant, permission, approval, or external effect is involved. Durability and idempotency are product features, not infrastructure footnotes: a human can leave, a service can restart, and Pub/Sub can redeliver without changing who holds authority or duplicating the side effect.

## Measured proof

The source gate passes 87 agent-runtime, 8 budget-guard, and 6 executor tests plus Go, strict TypeScript, compilation, static validation, credential scanning, and Terraform validation. A real Vertex mission used four `gemini-3.5-flash` ADK calls with native Agent Registry discovery and Agent Engine Sessions. The two specialist calls overlapped (7,416.848 ms and 6,007.249 ms); no timings or conclusions came from a fixture execution transcript.

## Open source

NoBS uses Mattermost Team Edition and the official plugin starter foundation. Original boundaries, pinned versions, licenses, and notices are documented in `UPSTREAM.md`, `docs/OSS_DISCLOSURE.md`, and `docs/CONTRIBUTION_MAP.md`.
