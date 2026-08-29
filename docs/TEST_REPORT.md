# NoBS Less Ping + Less Meeting Test Report

Verification date: **2026-08-29**

Release candidate: **`0.3.0`**

Local workspace: **`http://localhost:8065/acme/channels/project-atlas`**

Calendar workspace: **`http://localhost:8065/acme/nobs/calendar`**

Production remains on the previous image; this change was deployed and verified locally only.

## NoBS verification

| Layer | Proof | Result |
|---|---|---|
| branding and canonical route | login, product switcher, loading state, native shell, `/nobs`, and `/acme/nobs/calendar` | **NoBS visible; legacy `/noping` retained as redirect** |
| Calendar proof A | Atlas engineering sync | **30 → 0 minutes; all agenda items resolved; cancellation recommended** |
| Calendar proof B | Atlas launch readiness | **60 → 15 minutes; one human authority decision remains** |
| meeting exclusion | Welcome coffee | **deterministically skipped; no swarm started** |
| security | poisoned agenda/vendor instruction | **quarantined before synthesis and shown in the audit surface** |
| integration workroom | native private `Agent Workroom · Atlas` | **attendee agents, Atlas Agent, Gemini Enterprise, Gemini Code Assist, and GitHub seeded** |
| OOO | native account-menu action | **toggle verified; delegate handling and return-digest API active** |
| organizer authority | Calendar actions | **non-organizer rejected; ETag revalidation and explicit confirmation required** |
| responsive Calendar | Playwright 1440×900, 1024×600, 768×1024, 390×844 | **no document-level horizontal overflow** |
| focused browser suite | native delegate routing/identity, human-only delivery, NoBS panel, Calendar outcomes/skip, OOO, and responsive behavior | **all bounded stories passed** |
| Python runtime | `.venv/bin/pytest agent-service/tests -q` | **58 passed** |
| Go plugin | `GOCACHE=/tmp/nobs-go-cache go test ./...` | **all packages passed** |
| TypeScript | `npm --prefix plugin/webapp run typecheck` | **passed** |
| repository safety | static validation, credential scan, seed compile | **passed** |
| clean pinned client build | Mattermost webapp 11.10.1 overlay in Docker | **passed; upstream warnings only** |

## Verified

| Layer | Proof | Result |
|---|---|---|
| pinned native client | Mattermost webapp `11.10.1` at commit `f9deca984f8a8d38a5f5e50600b45e22c90ebca1` plus the reviewable NoBS source overlay | **passed** |
| reproducible client | two independent compiler runs from the same pristine pinned checkout/dependency layer; SHA-256 manifests compared for all 4,360 emitted non-source-map files | **byte-identical** |
| rendered shell | local `/` and `/login` HTML title, app metadata, favicons, and loading state | **NoBS; no case-insensitive `Mattermost` text** |
| aggregate source gate | `./scripts/check.sh` | **46 agent tests, 8 budget-guard tests, all Go packages, strict TypeScript, Python compile, shell/static/security checks passed** |
| native message hooks | `python3 scripts/verify-native-messaging.py` against the local Docker stack | **passed** |
| automatic exact routing | untagged `Why is Atlas delayed?` | **Project Atlas Delegate → Engineering Delegate → Sarah Chen Delegate → Security Delegate; 4 consulted, 0 interrupted** |
| personal scope routing | untagged `What is blocking Atlas security?` | **Sarah's Agent replies automatically in one native thread** |
| routine conversation | informational channel update with no request | **no agent run and no model spend** |
| broadcast messages | `@channel` post | **no agent run** |
| human-only delivery | leading `--direct @sarah` | **token stripped, `human_only` persisted, no model-call increase** |
| personal delegation | one human mention and one-to-one DM | **Sarah Chen represented by audited NoBS bot post** |
| coordinated delegation | multiple human mentions | **one organization run and one threaded reply** |
| security boundary | salary request by an unauthorized requester | **denied before disclosure and persisted with `noping_security_state=denied`** |
| plugin bundle | `com.noping.enterprise-0.3.0.tar.gz` | **built and installed locally** |

The integration test also proves idempotent single-post delivery, native threaded replies, stable compatibility post properties, and the preserved database/team/channel model.

## Remaining production release gates

- Immutable Google Cloud image/plugin deployment and production smoke/security/cost verification.
- Real Google Calendar OAuth must be re-consented with `calendar.events` before confirmed writes can be exercised against the dedicated demo account; local fixture-backed write safety is covered by Go tests.
- Native mobile applications remain out of scope.

## Cost and security controls retained

- Terraform rejects a budget above **$25**.
- Cloud Run services remain **min 0 / max 1**.
- Per-user and organization rate limits remain enforced.
- Daily model calls and token ceilings remain enforced.
- Model Armor, permission-aware retrieval, HMAC/OIDC service authentication, decision authority, audit events, and the budget guard remain in the release candidate.

## Rollback

The existing production image and plugin remain untouched. Their current immutable references must be captured immediately before deployment, and the new image must be promoted only after Chrome QA passes.
