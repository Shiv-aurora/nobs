# Failure and recovery

| Failure | Durable behavior | Recovery |
|---|---|---|
| Cloud Run instance interruption | completed step transitions remain in Firestore | resume the same mission; completed nodes are skipped |
| duplicate work event | stable event ID is an idempotent no-op | acknowledge without a second projection |
| malformed event | validation rejects bounded envelope | Pub/Sub retries, then dead-letters |
| model/tool failure | mission records safe failure; no fabricated answer | bounded operator/user resume after cause is fixed |
| Model Armor unavailable | production synthesis fails closed | retry after guard availability returns |
| unauthorized evidence | excluded before specialist context | report unresolved without data leakage |
| unauthorized checkpoint actor | checkpoint stays pending | current business approver or Calendar organizer resolves only their own gate |
| meeting ETag changed before approval | approval returns conflict and meeting becomes stale | rerun against a fresh snapshot |
| duplicate command delivery | terminal/leased command is a no-op | Pub/Sub redelivery is acknowledged safely |
| executor interruption after claim | lease expires; attempt is bounded | redelivery reclaims only after lease expiry |
| Calendar returns HTTP 412 | command becomes terminal `stale` | mission requires refresh/re-evaluation |
| postcondition cannot be verified | attempt fails; success is not claimed | bounded retry or manual review |
| model budget exhausted | new synthesis is denied before provider call | deterministic collaboration and cached state continue |

The current mission enum uses the implemented operational states `accepted`, `running`, `waiting_human`, `queued_action`, `completed`, and `failed`; stale Calendar commands use terminal `stale`. More granular named states remain a future schema evolution, not a deployed claim.
