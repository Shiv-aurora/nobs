# Google Cloud Deployment

## Live deployment

| Item | Value |
|---|---|
| project | `noping-agentic-shiv-2026` |
| region / zone | `us-central1` / `us-central1-a` |
| application | https://35-202-201-122.sslip.io/noping |
| agent service | `noping-agent-service` (private Cloud Run) |
| budget guard | `noping-budget-guard` (private Cloud Run, armed) |
| plugin | `com.noping.enterprise` version `0.2.1` |
| model | `gemini-3.5-flash`, Vertex location `global` |

The Mattermost VM service account mints a Google OIDC token for the exact Cloud Run audience, then the plugin adds a timestamped HMAC request signature. Pub/Sub uses its own pinned push identity. Cloud Run does not allow unauthenticated invocation.

Mattermost remains the collaboration substrate and system of record for users, channels, posts, threads, files, permissions, and realtime delivery. The registered `/noping` product route owns the visible shell, reads and writes those resources through the authenticated same-origin Mattermost API, and publishes `@noping` answers as a dedicated bot identity. Caddy serves the custom NoPing login and prevents the native desktop-app chooser from interrupting the browser flow.

## Reproducible deployment

Prerequisites are `gcloud`, Terraform, Docker, Git, Go, Node/npm, Python 3.11+, a dedicated billed project, and permissions for the services declared in Terraform.

```bash
cp deploy/gcp/terraform/terraform.tfvars.example deploy/gcp/terraform/terraform.tfvars
# Set project_id and billing_account_id; retain the bounded defaults.
deploy/gcp/scripts/deploy-all.sh
```

The deployment sequence performs cost preflight, two-stage Terraform, local secret-version creation, Model Armor configuration, immutable image builds, private Cloud Run rollout, Mattermost/plugin installation, deterministic organization seeding, a dry-run budget notification, and deployment verification. After reviewing the guard log:

```bash
deploy/gcp/scripts/arm-budget-guard.sh
```

The repository carries `.budget-guard-armed` as an ignored local marker, so later service deployments preserve `dry_run=false`.

## Compatibility decisions discovered in production

- Mattermost Team Edition `11.10.1` is distroless, so it has no shell or `curl`. Container-local shell health checks were removed; bootstrap probes the loopback-only host mapping `127.0.0.1:8065` instead.
- Replacing `/opt/noping` requires `docker compose --force-recreate` so containers receive the new bind mounts while named PostgreSQL/Mattermost volumes preserve data.
- The plugin archive path is derived from `plugin.json`; this prevents an old versioned archive from being silently redeployed.
- Cloud Run's edge did not forward the application's `/healthz` path in this deployment. Platform health still uses `/healthz`; signed plugin traffic uses the equivalent `/v1/health` alias.
- Vertex `gemini-3.5-flash` uses location `global`, and thinking output is bounded so the answer fits inside the application token ceiling.
- Traces are exported directly over authenticated OTLP HTTP to Google Telemetry with a simple processor. This works with request-based Cloud Run CPU and avoids an always-on collector.
- Google Calendar credentials remain optional at deployment time. When no authorized-user secret version exists, the connector announces and uses deterministic availability fallback rather than failing or pretending a live read occurred. The live deployment now has a real read-only authorized-user credential in Secret Manager.
- Personal Gmail calendars cannot create Google's native `outOfOffice` event type. NoPing additionally supports a privacy-tagged normal event (`nopingAvailability=out_of_office`) while still excluding titles, descriptions, locations, attendees, and attachments. Enterprise-native OOO events continue to work unchanged.

## Calendar authorization

Calendar uses the read-only `calendar.events.readonly` scope. For Workspace scopes, create a project-owned **Desktop app** OAuth client in Google Auth Platform, add the dedicated demo account as a test user, download the client JSON outside the repository, and complete interactive consent:

```bash
gcloud auth application-default login --launch-browser \
  --client-id-file=/secure/path/client_secret.json \
  --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/calendar.events.readonly
deploy/gcp/scripts/store-calendar-credentials.sh \
  "$HOME/.config/gcloud/application_default_credentials.json"
deploy/gcp/scripts/deploy-mattermost.sh
```

The connector maps only configured identities and projects and publishes normalized availability/work-state facts—not event descriptions or unrelated private calendar content. Production proof on 2026-08-28 showed a successful live read, one synchronized work-state event, one Firestore `calendar.out_of_office` record for `maya`, and `out_of_office` in the hosted bootstrap response.

## Verify and operate

```bash
deploy/gcp/scripts/verify-deployment.sh
deploy/gcp/scripts/resource-inventory.sh
deploy/gcp/scripts/start-demo.sh
deploy/gcp/scripts/stop-all.sh
```

Final verification passed with both Cloud Run services private and bounded to min 0/max 1. Use `stop-all.sh` after recording. Full teardown remains guarded by the explicit phrase `DESTROY-NOPING`.
