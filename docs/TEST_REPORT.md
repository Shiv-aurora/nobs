# Test and evaluation report

Verified 2026-08-30 from clean tracked source at commits `4a65f61` and `22fe77e`.

## Credential-free gate

| Suite | Command | Result |
|---|---|---|
| governed agent runtime | `python -m pytest agent-service/tests` | **87 passed** |
| budget guard | `(cd deploy/gcp/budget-guard && python -m pytest tests)` | **8 passed** |
| action executor | `(cd executor-service && python -m pytest tests)` | **6 passed** |
| Go plugin/runtime | `(cd plugin && go test ./...)` | **all packages passed** |
| React contracts | `npm --prefix plugin/webapp run typecheck` | **passed** |
| Python compilation | `python -m compileall ...` | **passed** |
| shell syntax/static manifests | `./scripts/check.sh` | **passed** |
| credential scan | `python scripts/secret_scan.py` | **passed** |
| Terraform | `terraform fmt`; `terraform validate` with Google `8.0.0` | **passed** |

## Architecture scenarios

| Scenario | Verified result |
|---|---|
| engineering sync | both versioned specialists execute; deterministic fixture program derives cancel recommendation from authorized source evidence; no demo command is created |
| launch readiness | safe evidence resolves routine work; security/authority item remains; mission waits at a durable organizer checkpoint |
| injected evidence | poisoned vendor source is absent from every specialist claim |
| restricted compensation | restricted content does not enter mission claims; existing API tests deny access before synthesis |
| resume | step IDs and attempt counts remain unchanged after resume; completed nodes do not rerun |
| unauthorized checkpoint | non-organizer receives 403 and mission stays `waiting_human` |
| demo/live write separation | demo approval mutates nothing; a synthetic `google_calendar` source creates exactly one ETag-bound approved command |
| duplicate command | succeeded delivery is an idempotent no-op |
| lease contention | active lease prevents simultaneous execution |
| stale ETag | Calendar precondition failure becomes terminal `stale` |
| bounded retry | command stops after configured maximum |
| preference isolation | only allowlisted explicit preference writes; `authority_effect=none`; mission authorization never reads memory |
| credential-shaped event | rejected with schema validation before ingestion |

## Live Google proof

A real four-call ADK mission completed on Vertex AI `gemini-3.5-flash`, with Model Armor configured, native Agent Registry discovery, Agent Engine Sessions, and overlapping specialist timings. The exact measured values are in `STATUS.md`.

## Pending production evidence

The final signed Cloud Run smoke, Firestore document inventory, private executor IAM check, trace query, and browser mission walkthrough must be captured after the final revision rollout. No external Calendar mutation will be performed merely to manufacture a test result; production action proof requires an organizer-approved dedicated demo event.
