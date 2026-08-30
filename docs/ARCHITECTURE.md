# Governed multi-agent architecture

NoBS uses a **Governed Coordinator with Parallel Specialist Agents, Durable Mission State, Human Authority Gates, and a Least-Privilege Action Executor**. The editable overview is [`architecture.mmd`](architecture.mmd) and the video-ready render is [`architecture.png`](architecture.png).

```mermaid
flowchart TB
  U[Employee] --> UI[NoBS React UI]
  UI <-->|HTTPS + WebSocket| MM[Mattermost + Go plugin]
  MM <--> PG[(PostgreSQL collaboration truth)]
  MM -->|IAM token + HMAC| GW[Private NoBS Gateway]
  PS[Pub/Sub work events] -->|OIDC, async| GW
  GW --> AG[Access Gate + Model Armor]
  DD[Delegate Directory: logical identities] --> AG
  AG --> MC[Meeting Mission Controller: Gemini 3.5]
  MC -->|parallel| WG[Work Graph Agent: Gemini 3.5]
  MC -->|parallel| PE[Policy Evidence Agent: Gemini 3.5]
  WG --> EC[Evidence Critic: deterministic]
  PE --> EC
  EC --> MR[Meeting Resolution Agent: Gemini 3.5]
  MR --> AU[Authority Gate: deterministic]
  AU --> HC[Human checkpoint]
  AU --> DONE[Complete without action]
  HC --> CB[Approved typed command]
  CB --> CQ[Pub/Sub command ID]
  CQ --> EX[Private Action Executor]
  EX -->|If-Match| CAL[Google Calendar]
  CAL -->|post-write read| EX
  EX --> FS[(Firestore mission authority)]
  MC <--> FS
  HC <--> FS
  REG[Google Agent Registry] --> MC
  SES[Vertex Sessions] <--> MC
  MEM[Memory Bank: preferences only] -.-> UI
  GW --> OBS[Logging + Trace + Monitoring]
  MC --> OBS
  EX --> OBS
```

Employee, project, team, and policy delegates are logical organizational identities. Meeting Mission, Work Graph, Policy Evidence, and Meeting Resolution are executable agent components; Evidence Critic and Authority Gate are executable deterministic workflow nodes.

## What actually executes

The meeting mission is a fixed graph, not a free-form swarm. The controller, Work Graph specialist, Policy Evidence specialist, and resolution synthesizer are typed Google ADK `LlmAgent` invocations on `gemini-3.5-flash`. The two specialists execute concurrently with independent reports and measured durations. Evidence Critic and Authority Gate are deterministic code because support validation and authority cannot be model decisions.

The Agent Registry contains four native service entries and Firestore stores each rich application manifest. The controller can route only to approved known specialist IDs. Agent Engine Sessions store ADK session events; Firestore, not Sessions, owns mission, checkpoint, command, and audit truth. Memory Bank stores only explicit non-authoritative preferences.

## Request and mission sequence

```mermaid
sequenceDiagram
  actor E as Employee
  participant P as Mattermost + plugin
  participant G as Private gateway
  participant F as Firestore
  participant C as Controller
  participant W as Work Graph
  participant Y as Policy Evidence
  participant R as Critic + Resolution
  participant H as Human authority

  E->>P: Prepare meeting
  P->>G: session-derived user + IAM + HMAC + trace
  G->>G: access, admission, Model Armor
  G->>F: create mission and controller step
  G->>C: typed agenda + approved registry
  C-->>F: typed plan
  par independent specialists
    C->>W: authorized work sources only
    W-->>F: source-cited report
  and
    C->>Y: authorized policy sources only
    Y-->>F: source-cited report
  end
  F->>R: accepted claims only
  R-->>F: resolutions + recommendation
  alt authority required
    F-->>H: durable checkpoint
    H->>G: approve or reject
    G->>F: resolve the same mission transactionally
  else no authority required
    F->>F: complete mission
  end
```

## Durable state machine

```mermaid
stateDiagram-v2
  [*] --> accepted
  accepted --> running
  running --> running: persist each completed node
  running --> waiting_human: authority gate
  running --> completed: no human action
  running --> failed: safe failure
  failed --> running: explicit resume
  waiting_human --> completed: reject / approve demo recommendation
  waiting_human --> queued_action: approve live command
  queued_action --> completed: executor verifies result
  queued_action --> failed: retry limit / uncertain verification
```

Completed step IDs and attempts are stable, so recovery skips them instead of fabricating or replaying successful agent work.

## Action execution sequence

```mermaid
sequenceDiagram
  participant H as Organizer
  participant G as Gateway/runtime
  participant F as Firestore
  participant Q as Pub/Sub
  participant X as Private executor
  participant C as Calendar

  H->>G: approve recommendation + expected ETag
  G->>F: resolve checkpoint; persist approved command
  G->>Q: command ID only
  Q->>X: authenticated at-least-once push
  X->>F: transactionally claim lease
  alt duplicate or terminal
    F-->>X: no-op
  else claimed
    X->>C: If-Match write
    C-->>X: provider result
    X->>C: read postcondition
    C-->>X: verified state
    X->>F: immutable attempt + result hash
  end
```

Seeded demo Calendar rows are deliberately non-writeable. Approval records an approved recommendation and generates no command. Only an ingested `source=google_calendar` snapshot can produce an executor command.

## Identity and permission boundaries

| Identity | Can read | Can write | Explicitly cannot |
|---|---|---|---|
| browser user | own Mattermost session/UI | normal UI requests | choose the server-side requester or call private Cloud Run directly |
| `noping-mattermost` | invoke gateway, publish normalized events | Mattermost plugin state/events | access the Calendar credential |
| `noping-agent` | Firestore projections, Vertex AI, Model Armor, Agent Registry | mission/checkpoint/proposal state and one command topic | access Calendar OAuth secret or call Calendar writes |
| `noping-pubsub-push` | none | mint OIDC for private push endpoints | business data, model, Calendar |
| `noping-action-executor` | approved commands and one Calendar credential | narrow Calendar action and verified result | Gemini, query APIs, arbitrary tools, other secrets |
| `noping-budget-guard` | configured VM state | stop only the demo VM | business data, budgets, models, deletion |

## State ownership

| State | Authority | Stored representation |
|---|---|---|
| users, sessions, channels, posts, files | Mattermost/PostgreSQL | native records |
| Calendar event content and revision | Google Calendar | compact meeting projection + ID/ETag |
| GitHub/Jira/source facts | original provider | bounded evidence metadata and work projection |
| mission, steps, checkpoints | Firestore | tenant-scoped typed documents |
| approved commands and attempts | Firestore | typed command, lease, immutable attempt, response hash |
| confirmed decision memory | Firestore | scope/facts/policy/authority/expiry-bound record |
| non-authoritative preferences | Vertex Memory Bank | allowlisted explicit preference only |
| ADK session events | Vertex Agent Engine Sessions | context, not business authority |
| agent lifecycle | Agent Registry + Firestore manifest | native discovery plus typed governance fields |
| prompts/raw private evidence | originating system / ephemeral request | not persisted in mission state or logs |

## Failure modes

| Failure | Safe behavior |
|---|---|
| Model Armor unavailable | production synthesis fails closed |
| source injection | scanner/Model Armor quarantines it before agent context |
| agent/model error | mission fails safely; no prewritten fallback answer |
| runtime restart | resume same mission and skip completed steps |
| unauthorized approver | 403; checkpoint remains pending |
| source ETag changed | reject approval/execution and require fresh preparation |
| duplicate event/command | transactional idempotent no-op |
| executor crash | bounded lease expiry permits safe redelivery |
| unverifiable provider result | never claim success; bounded retry/manual review |
| model budget exhausted | block new synthesis before the provider call |
| project budget threshold | independent guard can stop only the demo VM |

## Cost and scaling profile

| Component | Hackathon bound | Scale path |
|---|---|---|
| Mattermost/PostgreSQL/Caddy | one `e2-small` VM | normal Mattermost HA + managed database |
| agent gateway/runtime | Cloud Run min 0, max 1, concurrency 4 | raise cap; Firestore already owns state |
| action executor | Cloud Run min 0, max 1, concurrency 1 | partition only when measured |
| Firestore | native single-region database | managed autoscaling; retention/index review |
| Pub/Sub | retained work/command topics with DLQs | native throughput scaling |
| Gemini | four calls max per meeting mission | per-tenant admission/token budgets remain |

## Accurate platform choices

Google Agent Gateway is not shown as deployed. It governs A2A/MCP network calls, but this mission’s agents run in one process and the executor consumes an authenticated typed Pub/Sub command ID. There is no A2A/MCP hop for Gateway to mediate today. Agent code executes on private Cloud Run; the deployed Agent Engine resource supplies Sessions and Memory Bank, not an Agent Runtime deployment.
