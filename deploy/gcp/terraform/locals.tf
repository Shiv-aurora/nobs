data "google_project" "current" {
  project_id = var.project_id
}

locals {
  common_labels = merge(
    {
      app         = "noping"
      environment = var.environment
      managed_by  = "terraform"
      hackathon   = "all-things-agentic"
    },
    var.labels,
  )

  agent_service_name   = "${var.name_prefix}-agent-service"
  budget_guard_name    = "${var.name_prefix}-budget-guard"
  action_executor_name = "${var.name_prefix}-action-executor"
  mattermost_name      = "${var.name_prefix}-mattermost"
  budget_name          = "NoPing $25 guardrail"

  # Stable OIDC audiences avoid a Cloud Run service self-reference during the
  # first Terraform apply. They do not need to resolve in DNS; Cloud Run accepts
  # them as additional audiences while requests still use the generated URI.
  agent_service_audience   = "https://${var.project_id}.noping.internal/agent-service"
  budget_guard_audience    = "https://${var.project_id}.noping.internal/budget-guard"
  action_executor_audience = "https://${var.project_id}.noping.internal/action-executor"

  required_apis = toset([
    "aiplatform.googleapis.com",
    "agentregistry.googleapis.com",
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "calendar-json.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudtrace.googleapis.com",
    "compute.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "logging.googleapis.com",
    "modelarmor.googleapis.com",
    "monitoring.googleapis.com",
    "oslogin.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "serviceusage.googleapis.com",
    "telemetry.googleapis.com",
  ])

  agent_project_roles = toset([
    "roles/aiplatform.user",
    "roles/agentregistry.viewer",
    "roles/cloudtrace.agent",
    "roles/datastore.user",
    "roles/logging.logWriter",
    "roles/modelarmor.user",
    "roles/modelarmor.viewer",
    "roles/monitoring.metricWriter",
    "roles/serviceusage.serviceUsageConsumer",
    "roles/telemetry.tracesWriter",
  ])

  executor_project_roles = toset([
    "roles/cloudtrace.agent",
    "roles/datastore.user",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/telemetry.tracesWriter",
  ])

  vm_project_roles = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])
}
