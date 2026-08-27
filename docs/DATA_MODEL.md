# Data Model

## Organizational graph

NoPing uses a deliberately small relationship graph for routing rather than attempting to convert every company document into graph triples.

Primary nodes:

- `User`
- `Team`
- `Project`
- `WorkItem`
- `Policy`
- `Delegation`
- `Delegate`
- `Decision`
- `DecisionMemory`
- `Evidence`
- `WorkEvent`
- `SemanticWorkState`

Representative edges:

```text
user MEMBER_OF team
user WORKS_ON project
user OWNS work_item
work_item BLOCKS project
project REQUIRES policy
user DELEGATES authority TO user
entity REPRESENTED_BY delegate
query ROUTED_TO delegate
answer SUPPORTED_BY evidence
decision CREATES memory
```

The graph is for discovery, ownership, and authority. Detailed text remains in its source system and is retrieved under permission checks.

## Evidence

Every evidence record carries:

- stable ID and title;
- source type and URL;
- linked entity IDs;
- scope;
- observed timestamp;
- confidence;
- allowed roles;
- security state and reason.

Evidence is filtered before model context construction. Large production evidence should be referenced, not copied into Firestore.

## Work events

All connectors normalize to the same immutable envelope:

```text
id, source, event_type, actor_user_id, entity_ids, occurred_at, payload
```

The event ID is the idempotency key. The semantic projector mutates compact current state, but retains event references for provenance.

## Decisions and memory

A `Decision` is an asynchronous authority request. It contains:

- canonical decision key;
- title/summary;
- requester and assignee;
- optional project;
- options;
- evidence and policy references;
- due/status/resolution;
- facts hash.

A `DecisionMemory` is generated only from an explicit resolution. It is reusable only when canonical key, scope, facts hash, and expiry still match.

## Persistence split

- Mattermost/PostgreSQL: people, teams, sessions, rooms, messages, files, collaboration history.
- Firestore: compact query results, decisions, memory, work events, audit, counters, and semantic state.
- Pub/Sub: transient event transport with dead-letter handling.
- Source systems: original GitHub/Calendar/Jira records.
