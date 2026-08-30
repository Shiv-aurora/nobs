# Google Cloud Deployment

## Live deployment

| Item | Value |
|---|---|
| project | `noping-agentic-shiv-2026` |
| region / zone | `us-central1` / `us-central1-a` |
| application | https://35-202-201-122.sslip.io/acme/channels/project-atlas |
| agent service | `noping-agent-service` (private Cloud Run) |
| budget guard | `noping-budget-guard` (private Cloud Run, armed) |
| plugin | `com.noping.enterprise` version `0.3.0` |
| model | `gemini-2.5-flash`, Vertex location `global` |

The Mattermost VM service account mints a Google OIDC token for the exact Cloud Run audience, then the plugin adds a timestamped HMAC request signature. Pub/Sub uses its own pinned push identity. Cloud Run does not allow unauthenticated invocation.

Mattermost remains the collaboration substrate and system of record for users, channels, posts, threads, files, permissions, and realtime delivery. The deployment compiles a NoPing-branded client from the exact 11.10.1 source revision and packages it over the unchanged official Team Edition server binary. The Go plugin adds personal delegates, coordinated organizational routing, human-only delivery, native thread replies, and the contextual NoPing side panel. Caddy serves the NoPing login, redirects `/` and legacy `/noping` URLs into the native channel workspace, and prevents the desktop-app chooser from interrupting the browser flow.

## Reproducible deployment

Prerequisites are `gcloud`, Terraform, Docker, Git, Go, Node/npm, Python 3.11+, a dedicated billed project, and permissions for the services declared in Terraform.

```bash
cp deploy/gcp/terraform/terraform.tfvars.example deploy/gcp/terraform/terraform.tfvars
# Set project_id and billing_account_id; retain the bounded defaults.
deploy/gcp/scripts/deploy-all.sh
```

The deployment sequence performs cost preflight, two-stage Terraform, local secret-version creation, Model Armor configuration, immutable agent, guard, and pinned NoPing collaboration-client image builds, private Cloud Run rollout, plugin installation, deterministic organization seeding, a dry-run budget notification, and deployment verification. After reviewing the guard log:

```bash
deploy/gcp/scripts/arm-budget-guard.sh
```

The repository carries `.budget-guard-armed` as an ignored local marker, so later service deployments preserve `dry_run=false`.

## Compatibility decisions discovered in production

- Mattermost Team Edition `11.10.1` is distroless, so it has no shell or `curl`. Container-local shell health checks were removed; bootstrap probes the loopback-only host mapping `127.0.0.1:8065` instead.
- Replacing `/opt/noping` requires `docker compose --force-recreate` so containers receive the new bind mounts while named PostgreSQL/Mattermost volumes preserve data.
- The plugin archive path is derived from `plugin.json`; this prevents an old versioned archive from being silently redeployed.
- Cloud Run's edge did not forward the application's `/healthz` path in this deployment. Platform health still uses `/healthz`; signed plugin traffic uses the equivalent `/v1/health` alias.
- Vertex `gemini-2.5-flash` uses location `global`, and thinking output is bounded so the answer fits inside the application token ceiling.
- Traces are exported directly over authenticated OTLP HTTP to Google Telemetry with a simple processor. This works with request-based Cloud Run CPU and avoids an always-on collector.
- Google Calendar credentials remain optional at deployment time. When no authorized-user secret version exists, the connector announces and uses deterministic availability and meeting fixtures rather than failing or pretending a live read occurred.
- Personal Gmail calendars cannot create Google's native `outOfOffice` event type. NoBS additionally supports a privacy-tagged normal event (`nopingAvailability=out_of_office`). Meeting sync reads title, agenda, time, organizer, mapped attendees, update token, and private NoBS overrides only.

## Calendar authorization

Calendar uses `calendar.events` so confirmed organizer actions can cancel, shorten, or update the agenda. Use only the dedicated demo Google account—never a daily personal calendar. Create a project-owned **Desktop app** OAuth client in Google Auth Platform, add that demo account as a test user, download the client JSON outside the repository, and complete interactive consent:

```bash
gcloud auth application-default login --launch-browser \
  --client-id-file=/secure/path/client_secret.json \
  --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/calendar.events
deploy/gcp/scripts/store-calendar-credentials.sh \
  "$HOME/.config/gcloud/application_default_credentials.json"
deploy/gcp/scripts/deploy-mattermost.sh
```

The connector maps only configured identities and publishes compact availability and eligible-meeting projections. Calendar writes use the current event ETag and are never attempted until the mapped organizer explicitly confirms the recommendation in NoBS.

## Verify and operate

```bash
deploy/gcp/scripts/verify-deployment.sh
deploy/gcp/scripts/resource-inventory.sh
deploy/gcp/scripts/start-demo.sh
deploy/gcp/scripts/stop-all.sh
```

Final verification passed with both Cloud Run services private and bounded to min 0/max 1. Use `stop-all.sh` after recording. Full teardown remains guarded by the explicit phrase `DESTROY-NOPING`.
