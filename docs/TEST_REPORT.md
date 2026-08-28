# Phase 2 Test Report

Final verification date: **2026-08-28 UTC**

Google Cloud project: **`noping-agentic-shiv-2026`**

Hosted application: **https://35-202-201-122.sslip.io/noping**

## Automated verification

| Layer | Command / proof | Result |
|---|---|---|
| aggregate source gate | `make check` | **45 agent tests, 8 guard tests, all Go packages, strict TypeScript, Python compile, shell/static/security checks passed** |
| local product | Docker Compose Mattermost + plugin + agent, then Playwright | **4/4 passed across messaging, responsive, authority/memory, and malicious-input flows** |
| production messaging flow | real Project Atlas post + threaded `@noping` bot reply | **passed in 18.7 s** |
| production responsive flow | phone 390×844 + short laptop 1024×600, no horizontal overflow | **passed in 13.2 s** |
| production authority flow | Playwright against hosted Mattermost and private Cloud Run, including enforced cooldown retry | **passed in 1.5 min** |
| production safety flow | Playwright malicious prompt + reload + NoPing branding assertion | **passed in 15.5 s** |
| evidence capture | gated Playwright capture against production | **1/1 passed in 25.9 s** |
| Terraform | provider-backed validate, apply, and final plan | **passed; zero unplanned resources** |
| deployment contract | `deploy/gcp/scripts/verify-deployment.sh` | **passed; private Cloud Run, min 0/max 1, Mattermost reachable** |
| credentials | `scripts/secret_scan.py` and Secret Manager metadata review | **passed** |

The production authority flow proved all of the following in one browser journey:

- Maya received a sourced, four-delegate Atlas answer with zero interruptions;
- poisoned evidence was quarantined before synthesis;
- salary data was denied before retrieval or model execution;
- a security exception created exactly one complete decision for delegated approver Alex;
- Alex rejected it; and
- Priya's materially identical request reused scoped decision memory with zero new interruptions.

The production messaging flow additionally proved that the visible NoPing shell loads real Mattermost channels and seeded posts, Maya can publish a normal post, `@noping` invokes the private organizational agent, the dedicated NoPing bot joins through Mattermost's real team/channel membership model, and the answer is persisted as a threaded post with route and interruption metadata. The complete production suite reported **4 passed, 1 intentionally gated evidence-capture test skipped**. During the suite, the third rapid Maya query received the configured `429`/`Retry-After: 60`; the test honored the cooldown and then passed, proving that public model spend admission is active.

The original phrase “bypass security review” was correctly but over-conservatively rejected by live Model Armor. The production example now uses “Should Atlas launch for the $200K customer?”, which reaches the human-authority branch without weakening the separate malicious-prompt control.

The final local rerun rebuilt the agent image, installed plugin version `0.2.1`, and exercised the same messaging-first browser suite. That run also found and fixed a reproducibility defect in `scripts/install-plugin-local.sh`: the installer now derives the archive version from `plugin/plugin.json` instead of silently selecting the obsolete `0.1.0` bundle.

## Live Google Cloud evidence

- **Google ADK + Vertex AI:** `gemini-3.5-flash` in `global`; production run `run-5a37b31b9180` completed with one model call, 791 input tokens, 160 output tokens, four route hops, six authorized evidence records, and zero human interruptions.
- **Model Armor:** clean prompt accepted; malicious prompt rejected; response screening and fail-closed behavior exercised.
- **Cloud Run authentication:** unauthenticated external request returned `403`; unsigned, invalid-signature, and expired-replay HMAC requests returned `401`.
- **Firestore:** cold-start restoration retained normalized work state and audit records; a duplicate delivery did not create a second audit entry.
- **Pub/Sub:** authenticated push, duplicate suppression, and dead-letter inspection were exercised.
- **GitHub:** live signed webhook delivery GUID `14341326-a289-11f1-8f2e-cf446830ac6d` returned `202`; normalized `repository.pushed` state for `Shiv-aurora/noping` persisted exactly once.
- **Google Calendar:** a project-owned desktop OAuth client completed consent for the dedicated demo account with `calendar.events.readonly` plus `cloud-platform`. A privacy-minimal live read succeeded, the connector synchronized one tagged out-of-office work-state event, Firestore persisted exactly one `calendar.out_of_office` event for `maya`, and the deployed bootstrap returned `availability_status=out_of_office` with an expiry. The Calendar contained four clearly labeled demo meetings plus the tagged work-state block; no attendees or notifications were created. The deployed credential is read-only and event titles/descriptions are excluded from connector requests.
- **Trace:** Cloud Trace returned seven spans for trace `911bf362b57e01127de8d7999a4d2a9a`, including `/v1/bootstrap` receive/send spans.
- **Budget guard:** synthetic 90% notification was verified in dry-run, then the guard was armed; current Cloud Run setting is `dry_run=false`.

## Captured browser evidence

- [`phase2-organization-answer.png`](evidence/phase2-organization-answer.png)
- [`phase2-decision-memory.png`](evidence/phase2-decision-memory.png)
- [`phase2-audit-trail.png`](evidence/phase2-audit-trail.png)
- [`phase2-agent-operations.png`](evidence/phase2-agent-operations.png)
- [`phase2-messaging-agent-reply.png`](evidence/phase2-messaging-agent-reply.png) — messaging-first channel with inline delegate reply
- [`phase2-messaging-phone.png`](evidence/phase2-messaging-phone.png) — 390×844 responsive proof
- [`phase2-messaging-short-laptop.png`](evidence/phase2-messaging-short-laptop.png) — 1024×600 responsive proof

Refresh these artifacts explicitly with:

```bash
NOPING_CAPTURE_EVIDENCE=true \
MATTERMOST_URL=https://35-202-201-122.sslip.io \
NOPING_DEMO_USER_PASSWORD="$(gcloud secrets versions access latest --secret=noping-demo-user-password)" \
npm --prefix e2e test -- evidence.spec.ts
```

## Known limitations

- Native Google Calendar `outOfOffice` events require an enterprise Calendar. The dedicated personal demo account therefore uses a private `nopingAvailability=out_of_office` marker on a normal event; NoPing queries that marker without requesting the event title, description, location, attendees, or attachments. Native enterprise OOO events remain supported by the same connector.
- The judging URL uses Caddy-managed TLS with the stable `sslip.io` hostname. A custom first-party domain remains a post-hackathon branding improvement.
- Mattermost email notifications are intentionally unconfigured for the demo.
- The repository is private; no irreversible visibility change was made without owner approval.
- The fixed VM should be stopped after demo recording; Cloud Run already scales to zero.

Phase 1 remains marked by tag `phase1-complete`; Phase 2 adds real provider, connector, browser, cost-control, and observability evidence without rewriting Phase 1 history.
