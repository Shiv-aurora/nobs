# Google Cloud deployment

## Verified target

| Setting | Value |
|---|---|
| project | `noping-agentic-shiv-2026` |
| primary region | `us-central1` |
| primary model | Vertex AI `gemini-3.5-flash`, location `global` |
| mission runtime | private Cloud Run `noping-agent-service` |
| durable state | Firestore Native `(default)` |
| agent lifecycle | Google Agent Registry `global`, four service entries |
| agent context | Agent Engine `1977754786799288320`, `us-central1` Sessions/Memory Bank |
| safety | Model Armor `noping-enterprise-guard`, fail closed |
| action boundary | private Cloud Run `noping-action-executor` with dedicated identity |
| event/command transport | Pub/Sub with OIDC push and DLQs |
| collaboration | existing `noping-mattermost` VM, Caddy, Mattermost, PostgreSQL |
| protection | existing $25 budget and private budget guard |

Visible product naming is NoBS. Internal `noping-*` resource names remain for compatibility.

## Reproducible flow

1. Run `./scripts/check.sh` and `terraform fmt -recursive deploy/gcp/terraform`.
2. Run `terraform -chdir=deploy/gcp/terraform init -backend=false` and `validate`.
3. Run the cost preflight; never create another project or raise the $25 budget.
4. Build Linux/AMD64 agent, executor, budget guard, and pinned Mattermost images; push to the existing Artifact Registry and deploy by digest.
5. Apply Terraform or use the checked-in commands/scripts to create only the bounded APIs, service accounts, IAM, topics, subscriptions, private Cloud Run revisions, registry services, and secrets references.
6. Keep Cloud Run min 0/max 1; gateway concurrency 4 and executor concurrency 1.
7. Install the plugin/NoBS web image on the existing VM without replacing PostgreSQL data.
8. Run signed private-service smoke tests, production browser tests, IAM checks, Firestore/trace/log evidence, and budget verification.
9. Stop the demo VM after final verification according to the operating procedure when it need not remain available.

## Required secret boundaries

- `noping-service-signing-secret`: gateway only (and the VM side already configured to sign).
- `noping-google-calendar-credentials`: action executor only after explicit IAM approval.
- Mattermost/PostgreSQL/demo passwords: existing VM/deployment path only.

Never print secret values, store them in Terraform state as plaintext variables, or commit generated `.env` files.

## Verification commands

```bash
./scripts/check.sh
terraform -chdir=deploy/gcp/terraform validate
gcloud run services list --project=noping-agentic-shiv-2026 --region=us-central1
gcloud pubsub topics list --project=noping-agentic-shiv-2026
gcloud iam service-accounts list --project=noping-agentic-shiv-2026
gcloud logging read 'resource.type="cloud_run_revision"' --project=noping-agentic-shiv-2026 --limit=20
```

Inspect IAM for every service and confirm no private service contains `allUsers`. Confirm the agent service account has no access to the Calendar secret and the executor has no Vertex AI/Model Armor role. Confirm model logs/traces contain only safe identifiers and `gemini-3.5-flash`.

## Platform disclosure

Agent code executes on private Cloud Run. Agent Engine is used for Sessions and preference-only Memory Bank. Agent Gateway is not deployed because no current critical-path call uses A2A or MCP. These distinctions must remain unchanged in the diagram and submission unless the deployment changes.
