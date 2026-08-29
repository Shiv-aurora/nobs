# NoBS Less Ping + Less Meeting Test Report

Verification date: **2026-08-29**

Release candidate: **`0.3.0`**

Production workspace: **`https://35-202-201-122.sslip.io/acme/channels/project-atlas`**

Production Calendar: **`https://35-202-201-122.sslip.io/acme/nobs/calendar`**

Production collaboration image: **`nobs-release:fe2bdb8d76c8`**, loaded from the published image with digest **`sha256:64e3b985885842e7d1cf5b8eb804c567f4d05095a9fbb56fba034481a36ea567`**.

Production agent revision: **`noping-agent-service-00008-2xp`**, image digest **`sha256:2da4469b5dbb7c04d7329d09fb84568b86526bb48451032ec30f7bc74fc08da6`**.

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
| production browser suite | one-click demo entry, native delegate routing/identity, restricted denial, human-only delivery, NoBS panel, Calendar outcomes/skip, OOO, responsive behavior, and native collaboration controls | **13 passed, 1 intentionally skipped evidence-only capture, 0 failed in 2.8 minutes** |
| production login | public `Enter demo workspace` button | **same-origin POST creates a 12-hour non-admin session; no password is shipped to the browser; Calendar redirects preserved** |
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
| aggregate source gate | `./scripts/check.sh` | **58 agent tests, 8 budget-guard tests, all Go packages, strict TypeScript, Python compile, shell/static/security checks passed** |
| native message hooks | `python3 scripts/verify-native-messaging.py` against the local Docker stack | **passed** |
| automatic exact routing | untagged `Why is Atlas delayed?` | **Project Atlas Delegate → Engineering Delegate → Sarah Chen Delegate → Security Delegate; 4 consulted, 0 interrupted** |
| personal scope routing | untagged `What is blocking Atlas security?` | **Sarah's Agent replies automatically in one native thread** |
| routine conversation | informational channel update with no request | **no agent run and no model spend** |
| broadcast messages | `@channel` post | **no agent run** |
| human-only delivery | leading `--direct @sarah` | **token stripped, `human_only` persisted, no model-call increase** |
| personal delegation | one human mention and one-to-one DM | **Sarah Chen represented by audited NoBS bot post** |
| coordinated delegation | multiple human mentions | **one organization run and one threaded reply** |
| security boundary | salary request by an unauthorized requester | **denied before disclosure and persisted with `noping_security_state=denied`** |
| plugin bundle | `com.noping.enterprise-0.3.0.tar.gz` | **built and enabled in production as NoBS 0.3.0** |
| production Cloud Run | private IAM and live service revision | **Ready; no `allUsers` or `allAuthenticatedUsers`; real Vertex AI/Gemini requests observed in Cloud Logging** |
| production cost guard | project-filtered `$25` budget, private budget-guard service, custom VM-stop role | **armed with `dry_run=false`; VM remains `e2-small`, disk 20 GB, both Cloud Run services min 0/max 1** |
| post-verification shutdown | Compute Engine instance status | **`noping-mattermost` stopped after the final production suite; restart with `deploy/gcp/scripts/start-demo.sh`** |

The integration test also proves idempotent single-post delivery, native threaded replies, stable compatibility post properties, and the preserved database/team/channel model.

## Known limitations and remaining operator actions

- The dedicated demo Google Calendar account is the only authorized account. Confirmed Calendar writes still require `calendar.events` consent; fixture-backed write safety and organizer confirmation are covered by Go tests.
- The public production demo reset endpoint is intentionally disabled. Production browser tests preserve completed meeting proof and prepare only meetings that remain ready.
- The VM service account intentionally has no Artifact Registry reader role. The verified release was transferred as a checksum-verified Docker archive over IAP and loaded locally, avoiding a broader IAM change.
- GitHub push remains an operator action because exporting the complete local history and tags requires explicit user approval.
- Native mobile applications remain out of scope.

## Cost and security controls retained

- Terraform rejects a budget above **$25**.
- Cloud Run services remain **min 0 / max 1**.
- Per-user and organization rate limits remain enforced.
- Daily model calls and token ceilings remain enforced.
- Model Armor, permission-aware retrieval, HMAC/OIDC service authentication, decision authority, audit events, and the budget guard remain in the release candidate.

## Rollback

The prior Compose environment, Caddy configuration, plugin bundle, and upstream Mattermost image were copied to `/opt/noping/rollback/pre-fe2bdb8d76c8` before promotion. Every failed installer attempt restored the previous healthy release automatically. The current VM reports `nobs-release:fe2bdb8d76c8` healthy and NoBS 0.3.0 enabled.
