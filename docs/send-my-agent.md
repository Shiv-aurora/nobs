# Send My Agent

Send My Agent is a native NoBS Calendar workflow. It keeps Mattermost as the
collaboration shell and extends the existing NoBS plugin and private agent
service; it does not introduce a second application or always-on service.

## Runtime path

1. An attendee chooses **Attend**, **Send my Agent**, or **Decline** on a NoBS
   Calendar event. Agent attendance is stored as a NoBS plan and does not alter
   the human's Google Calendar RSVP.
2. The mission editor accepts `tell`, `ask`, registered capability IDs, and
   escalation conditions. Server-owned policy escalations are always added and
   free text cannot grant authority.
3. Before the huddle starts, the service revalidates the Calendar ETag and
   participant snapshot. The plugin issues a short-lived session nonce.
4. The browser streams 16-bit mono 16 kHz PCM in 30 ms frames to the same-origin
   plugin WebSocket. The plugin binds the represented employee, meeting,
   delegation, and nonce to a private OIDC/HMAC WebSocket connection.
5. In production, the existing Cloud Run service uses ADK `Runner.run_live()`
   with the configured Vertex Live model. The local demo adapter exercises the
   same control, policy, tool, interruption, reconnect, and handoff contracts
   without incurring model spend.
6. Only structured outcomes, counters, resumption state, and audit references
   are durable. Raw audio and full transcripts are never persisted.
7. At an explicit end, production reserves one call against the existing text
   model budget for a concise handoff summary. The deterministic Told, Asked,
   Answers, Decisions, and For You fields remain authoritative if synthesis is
   blocked or fails; the local demo makes no handoff model call.

## Authorization

Every answer passes four deterministic checks: the representative may know the
fact, every current participant may receive it, the statement has approved
support, and the mission grants any required action. Sharing uses the
intersection of participant permissions. Missing or ambiguous permission,
private employee data, and authority-bearing decisions fail closed into a
handoff escalation.

## Limits

- one concurrent Live meeting;
- 15 minutes per session;
- 24 live tool calls per session;
- five scoped reconnect attempts per session nonce;
- 60 live minutes per organization per day;
- new sessions stop at 80% of the Live allocation;
- Cloud Run remains `min=0`, `max=1`, with a 3600-second timeout;
- the existing `$25` project budget guard remains authoritative.

The Live model ID and location are configuration, while `google-adk==2.8.0` and
`google-genai==2.20.0` are pinned for reproducible production builds.
