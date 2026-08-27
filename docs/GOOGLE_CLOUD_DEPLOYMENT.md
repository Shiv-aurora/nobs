# Google Cloud Deployment

## Prerequisites

- a dedicated Google Cloud project with billing attached;
- `gcloud`, Terraform 1.16+, Docker, Git, Go 1.23+, Node 22+, npm, Python 3.11+;
- permission to enable APIs, create service accounts/IAM, Compute, Cloud Run, Firestore, Pub/Sub, Artifact Registry, Secret Manager, Model Armor, and budgets;
- a billing account ID if the Terraform budget should be created.

## Configure

```bash
cp deploy/gcp/terraform/terraform.tfvars.example deploy/gcp/terraform/terraform.tfvars
```

Set at minimum:

```hcl
project_id         = "your-project-id"
billing_account_id = "000000-000000-000000"
```

Keep the default `e2-small`, 20 GB `pd-standard`, `$25` budget, Cloud Run max 1/min 0, and daily shutdown unless measured evidence justifies the approved `e2-medium` fallback.

## Automated two-stage deployment

```bash
deploy/gcp/scripts/deploy-all.sh
```

The script sequence:

1. preflight and cost-policy checks;
2. stage-one Terraform for APIs, IAM, network, VM, topics, secrets, Firestore, and registry;
3. add secret versions locally without putting values in Terraform state;
4. create Model Armor template;
5. build and push images, then resolve immutable digests;
6. stage-two Terraform for private Cloud Run and authenticated push subscriptions;
7. package/install the Mattermost plugin and seed the demo organization;
8. publish a synthetic 90% billing notification while the budget guard is dry-run;
9. verify IAM/scaling/VM and application reachability.

After inspecting budget-guard logs:

```bash
deploy/gcp/scripts/arm-budget-guard.sh
```

This requires typing `ARM` and redeploys only the guard setting.

## Start and stop

```bash
deploy/gcp/scripts/start-demo.sh
deploy/gcp/scripts/stop-all.sh
```

Cloud Run has minimum instances zero. `stop-all.sh` stops the only fixed Compute Engine workload.

## Verify

```bash
deploy/gcp/scripts/verify-deployment.sh
deploy/gcp/scripts/resource-inventory.sh
```

Append real command output and screenshots to `docs/COST_MODEL.md` and `docs/TEST_REPORT.md` before submission.

## Teardown

```bash
deploy/gcp/scripts/teardown.sh
```

The script requires typing `DESTROY-NOPING` and supplies the same second-stage image variables so Terraform can destroy all managed resources consistently.
