# Devpost Submission Draft

## Project name

NoPing

## Tagline

Ask the company, not a coworker.

## Track

Google All Things Agentic Hackathon — Fortified Enterprise Fleet.

## Inspiration

Workplace chat made everyone reachable, but it also made every question an interruption. The information needed to answer a routine question is usually already spread across channels, pull requests, calendars, policies, and prior decisions. NoPing asks what workplace communication would look like if chat had been invented after trustworthy AI agents existed.

## What it does

NoPing is a messaging-first workplace communication layer built on Mattermost. Employees keep normal channels, messages, threads, files, permissions, and realtime collaboration. People write naturally: NoPing performs a model-free scope check on each human message, then lets the responsible employee or organization delegate answer routine work automatically. No bot tag is required. NoPing routes across permission-aware employee, project, team, policy, and authority delegates; retrieves only authorized evidence; and posts a sourced answer back into the thread.

For the Project Atlas demo, Maya asks why the launch is delayed. NoPing consults four delegates, blocks a poisoned vendor note, explains the real security blocker, and interrupts zero people. A salary request is denied before private HR data is retrieved or sent to Gemini. A genuine launch exception cannot be decided by the model: Sarah's calendar availability and delegated authority route one complete Needs You card to Alex. Alex's answer becomes scoped, expiring decision memory, so the same question can be answered later without another interruption.

## How we built it

- Mattermost Team Edition and PostgreSQL provide the collaboration substrate and system of record for identity, channels, posts, threads, files, permissions, and realtime delivery.
- A Go Mattermost plugin is the trusted boundary. It resolves the authenticated Mattermost user, proxies signed requests to the agent runtime, publishes websocket updates, provisions the NoPing bot, and writes agent answers as real threaded posts.
- A NoPing-branded build of the pinned mature web client owns the visible shell. The React/TypeScript plugin adds inline delegate identity, route metadata, native actions, and one contextual panel for Needs You, employee context, attention, and audit.
- A FastAPI agent service uses Google ADK and Vertex AI Gemini 3.5 Flash for bounded synthesis and a deterministic delegate graph for routing and authority enforcement.
- Model Armor screens prompts and responses. Evidence authorization happens before retrieval, and human-only authority outcomes are structurally unavailable to the model.
- Firestore stores compact work state, audit records, and decision memory. Pub/Sub ingests signed, idempotent GitHub, Calendar, and Mattermost events with OIDC push and a dead-letter path.
- Google Cloud deployment uses private Cloud Run services, Secret Manager, Artifact Registry, Cloud Logging, Monitoring, Trace, and one bounded `e2-small` Compute Engine VM running Caddy, Mattermost, and PostgreSQL.

## Challenges

The hardest work was preserving a real collaboration platform while making NoPing feel like the product. We kept the mature infrastructure and native channel client, compiled a reviewable NoPing source overlay at an exact upstream revision, and implemented agents through supported message hooks and extension surfaces. Production also exposed practical compatibility issues: a distroless server image, plugin bundle version drift, Cloud Run health-path behavior, OAuth constraints for personal Calendar accounts, and model-safety wording that correctly failed closed but required a clearer authority-demo prompt.

## Accomplishments

- A real messaging-first product rather than a standalone dashboard or chatbot mock.
- Automatic scope-matched answers persisted as native Mattermost thread replies under an audited delegate identity.
- Four-delegate organizational routing with visible evidence and zero-human resolution metrics.
- Pre-retrieval HR denial, malicious-content quarantine, and Model Armor prompt/response enforcement.
- OOO-aware human authority escalation and reusable scoped decision memory.
- Live GitHub and read-only Google Calendar work-state connectors.
- Private, zero-idle-agent Google Cloud architecture with Terraform zero drift and an armed $25 cost guardrail.
- Local and production browser suites covering messaging, responsive layouts, authority/memory, and malicious input.

## What we learned

The useful unit of enterprise agent design is not “one chatbot per employee.” It is a permissioned logical delegate with explicit evidence scope, authority boundaries, freshness, and auditability. We also learned that AI communication feels natural when it appears inside existing conversations, while analytics and organizational views work better as secondary surfaces. Finally, cost and security controls need to be executable product behavior: NoPing's browser test actually encountered the three-per-minute model admission limit, honored `Retry-After`, and completed after the enforced cooldown.

## What's next

- Connect a first-party domain and enterprise SSO.
- Sync production directory groups and project mappings instead of demo fixtures.
- Add native branded mobile clients and push notifications.
- Expand connector coverage while preserving source permissions and metadata-minimal event projection.
- Add high-availability Mattermost/PostgreSQL topology only when real usage justifies it.

## Links

- Live application: https://35-202-201-122.sslip.io/acme/channels/project-atlas
- Source repository: https://github.com/Shiv-aurora/noping
- Architecture: `docs/architecture.png`
- Four-minute narration: `docs/DEMO_SCRIPT.md`
- Verification evidence: `docs/TEST_REPORT.md`
- Public demo video: add the final YouTube/Vimeo URL after recording

## Technologies used

Google ADK, Vertex AI Gemini 3.5 Flash, Model Armor, Cloud Run, Compute Engine, Firestore, Pub/Sub, Secret Manager, Artifact Registry, Cloud Logging, Monitoring, Trace/OpenTelemetry, Terraform, Mattermost, PostgreSQL, Go, React, TypeScript, FastAPI, Python, Docker, and Playwright.

## Open-source disclosure

NoPing uses Mattermost Team Edition and the official Mattermost Plugin Starter Template pinned at upstream commit `3296cf6fad808c2372c254cf7b64bcc8a2144e67`. Original contribution boundaries and licenses are documented in `UPSTREAM.md`, `docs/OSS_DISCLOSURE.md`, and `docs/CONTRIBUTION_MAP.md`.
