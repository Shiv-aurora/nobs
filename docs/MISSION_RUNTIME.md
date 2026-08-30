# Durable meeting mission runtime

NoBS turns one meeting snapshot into one persisted, bounded mission.

1. Access and meeting membership are checked before mission creation.
2. The Gemini 3.5 controller produces a typed plan using approved agent IDs only.
3. Work Graph and Policy Evidence agents execute concurrently with separate typed outputs.
4. The deterministic critic rejects inaccessible, stale, low-confidence, conflicting, or unsupported claims.
5. The Gemini 3.5 synthesizer receives only accepted claims and returns exactly one resolution per agenda item.
6. An authority-bound agenda item carries `authority_type`; the deterministic `PolicyEngine` resolves the current business decision owner and persists that checkpoint.
7. Business approval resumes the same mission into a distinct Calendar gate. Only the meeting organizer can resolve that gate.
8. Demo meetings can record both approvals but never create an external command.
9. A live `google_calendar` meeting creates one ETag-bound command only after both applicable approvals.
10. Pub/Sub delivers only the command ID to the separate executor; the executor reloads both checkpoints and verifies the external postcondition.

Every node has a deterministic step identity, attempt, timestamps, measured duration, output references, agent ID/version where applicable, and trace linkage. Resume skips completed steps. Production uses UTC wall time; the fixed narrative clock exists only in deterministic tests.

Model use is admitted before execution: one mission reserves four calls, bounded input, and 2,400 total output tokens. A failed or interrupted mission keeps the full reservation charged conservatively.

No prompts, hidden reasoning, raw credentials, unrestricted message bodies, or full poisoned evidence are persisted in mission state or logs.
