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

  agent_service_name = "${var.name_prefix}-agent-service"
  budget_guard_name  = "${var.name_prefix}-budget-guard"
  mattermost_name    = "${var.name_prefix}-mattermost"
  budget_name        = "NoPing $25 guardrail"

  required_apis = toset([
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
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
  ])

  agent_project_roles = toset([
    "roles/aiplatform.user",
    "roles/cloudtrace.agent",
    "roles/datastore.user",
    "roles/logging.logWriter",
    "roles/modelarmor.user",
    "roles/modelarmor.viewer",
    "roles/monitoring.metricWriter",
  ])

  vm_project_roles = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])
}
