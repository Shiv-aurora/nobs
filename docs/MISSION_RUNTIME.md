# Durable meeting mission runtime

NoBS turns one meeting snapshot into one persisted, bounded mission.

1. Access and meeting membership are checked before mission creation.
2. The Gemini 3.5 controller produces a typed plan using approved agent IDs only.
3. Work Graph and Policy Evidence agents execute concurrently with separate typed outputs.
4. The deterministic critic rejects inaccessible, stale, low-confidence, conflicting, or unsupported claims.
5. The Gemini 3.5 synthesizer receives only accepted claims and returns exactly one resolution per agenda item.
6. The deterministic authority gate either completes the recommendation or persists a human checkpoint.
7. Demo meetings can record an approved recommendation but never create an external command.
8. A live `google_calendar` meeting creates one ETag-bound command only after authorized approval.
9. Pub/Sub delivers only the command ID to the separate executor; the executor verifies the external postcondition.

Every node has a deterministic step identity, attempt, timestamps, measured duration, output references, agent ID/version where applicable, and trace linkage. Resume skips completed steps. Production uses UTC wall time; the fixed narrative clock exists only in deterministic tests.

Model use is admitted before execution: one mission reserves four calls, bounded input, and 2,400 total output tokens. A failed or interrupted mission keeps the full reservation charged conservatively.

No prompts, hidden reasoning, raw credentials, unrestricted message bodies, or full poisoned evidence are persisted in mission state or logs.
