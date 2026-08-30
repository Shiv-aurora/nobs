# Architecture decisions

These decisions define the deployed NoBS architecture. “Agent” means an executable program; employee, project, team, policy, and authority delegates are organizational records.

## ADR-001 — Governed coordinator, not an unrestricted swarm

Status: accepted.

The Meeting Mission Controller creates a bounded plan and may route only to approved registry entries. Work Graph and Policy Evidence execute in parallel, then a deterministic critic, a resolution agent, a deterministic business-decision gate, and a distinct organizer-only Calendar gate run in fixed order. This gives the model enough freedom for open-ended evidence synthesis without allowing unbounded agent creation, recursive conversation, authorization, or side effects.

## ADR-002 — Logical delegates are not deployed agents

Status: accepted.

Employee, project, team, policy, and authority delegates describe represented entities, scope, relationships, evidence boundaries, and authority context. They do not execute code. Treating them as processes would create fake execution claims, unnecessary identities, and an unbounded deployment topology. `DelegateDirectory` owns this model; the Executable Agent Registry owns versioned programs.

## ADR-003 — Specialists share one runtime

Status: accepted.

The controller, two specialists, critic, and synthesizer have one owner, mission, release lifecycle, and context contract. They therefore share the private agent Cloud Run service. Separate services would add network and identity failure modes without increasing isolation; the consequential write path is the boundary that merits a separate service.

## ADR-004 — Consequential writes use a separate executor

Status: accepted; production rollout requires the explicitly approved executor IAM grant recorded in `STATUS.md`.

The gateway and model runtime do not receive the Calendar credential. An approved command is stored first, then Pub/Sub sends only its ID to a private single-concurrency executor. The executor reloads authoritative state, claims a lease transactionally, applies an ETag precondition, reads the result, hashes the provider response, and persists an immutable attempt. This prevents an agent from self-authorizing or directly writing Calendar.

## ADR-005 — Firestore owns mission state

Status: accepted.

Mission runs, steps, checkpoints, commands, attempts, counters, decision memory, agent manifests, compact work state, and audits must outlive a Cloud Run instance. Firestore transactions make state transitions, checkpoint resolution, lease claims, and duplicate suppression durable. Process memory remains a deterministic local adapter and a cache, never the distributed authority.

## ADR-006 — Mattermost/PostgreSQL remains collaboration authority

Status: accepted.

Users, sessions, memberships, channels, posts, threads, files, and realtime delivery already have a mature source of truth. NoBS extends that system through a Go plugin rather than copying collaboration state into a new database.

## ADR-007 — Decision memory and preference memory are separate

Status: accepted.

Confirmed decisions remain in Firestore with fact, scope, policy, actor, authority, outcome, and expiry checks. Vertex Agent Engine Memory Bank stores only explicit preferences from an allowlist (`brief_detail`, `calendar_view`, `digest_frequency`, `timezone`) with `authority_effect=false`. Mission authorization never reads preference memory.

## ADR-008 — Deterministic policy precedes model execution

Status: accepted.

Identity, tenant, requester roles, entity scope, evidence permission, policy, and delegation are evaluated before any model sees data. Gemini may summarize authorized policy evidence, but cannot grant scope, waive a rule, select the approving human, or approve a command.

## ADR-009 — Pub/Sub is at-least-once

Status: accepted.

NoBS assumes events and command IDs can be duplicated, delayed, or reordered. Stable IDs, source versions, Firestore transactions, leases, terminal states, and bounded retries make repeated delivery safe. The design does not claim perfect exactly-once transport.

## ADR-010 — Effectively-once side effects

Status: accepted.

Command IDs and deterministic idempotency keys prevent duplicate intent; a compare-and-set lease prevents simultaneous work; Calendar `If-Match` rejects stale state; post-write reads verify the result; immutable attempts record each outcome. Together these controls provide effectively-once behavior without making an unsupportable exactly-once claim.

## ADR-011 — No GKE, mesh, graph database, or service per agent

Status: accepted.

The bounded workload has no measured need for cluster scheduling, service-mesh policy, graph persistence, or independently scaled specialist services. Cloud Run, Firestore, Pub/Sub, and typed in-process graph nodes provide the needed durability and isolation at lower cost and operational risk.

## ADR-012 — Scale beyond the demo profile

Status: accepted.

The hackathon profile deliberately caps Cloud Run at one instance and Mattermost at one `e2-small` VM. The contracts remain horizontally scalable: Firestore owns state, Pub/Sub absorbs bursts, steps are idempotent, agents are versioned, and the plugin protocol is stateless. A production rollout can raise Cloud Run bounds and move Mattermost/PostgreSQL to its normal HA topology without changing mission semantics.

## ADR-013 — Agent Registry plus typed local manifests

Status: accepted.

Four executable services are registered in native Google Agent Registry. NoBS also persists its richer typed manifest—schema names, capabilities, tools, scopes, identity, model, version, and health—in Firestore because the registry’s generic service record does not replace application-level governance. Runtime discovery is considered native only when all required service IDs resolve.

## ADR-014 — Agent Engine Sessions and Memory Bank, Cloud Run execution

Status: accepted.

Vertex Agent Engine resource `1977754786799288320` provides durable ADK Sessions and preference-only Memory Bank. Executable code remains on private Cloud Run because that is the available, already secured runtime in this project. Firestore remains authoritative for business state; Sessions own ADK conversation events, not approvals or commands.

## ADR-015 — No Agent Gateway on an in-process path

Status: accepted.

Google Agent Gateway governs A2A and MCP network hops. The current specialists execute inside one owner/runtime and the executor consumes a typed command ID over authenticated Pub/Sub; neither critical path makes an A2A or MCP call. Adding Gateway would not mediate a tool call. The architecture will adopt it when an external A2A/MCP tool is introduced, and until then does not claim it as deployed.
