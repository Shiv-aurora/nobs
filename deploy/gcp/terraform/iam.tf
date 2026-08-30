resource "google_service_account" "agent" {
  account_id   = "${var.name_prefix}-agent"
  display_name = "NoPing Agent Runtime"
  description  = "Least-privilege identity for the private Cloud Run agent service."

  depends_on = [google_project_service.required["iam.googleapis.com"]]
}

resource "google_service_account" "mattermost" {
  account_id   = "${var.name_prefix}-mattermost"
  display_name = "NoPing Mattermost"
  description  = "Identity used by the Mattermost VM to invoke NoPing and publish approved work events."

  depends_on = [google_project_service.required["iam.googleapis.com"]]
}

resource "google_service_account" "pubsub_push" {
  account_id   = "${var.name_prefix}-pubsub-push"
  display_name = "NoPing Pub/Sub Push"
  description  = "OIDC identity used only by authenticated Pub/Sub push subscriptions."

  depends_on = [google_project_service.required["iam.googleapis.com"]]
}

resource "google_service_account" "budget_guard" {
  account_id   = "${var.name_prefix}-budget-guard"
  display_name = "NoPing Budget Guard"
  description  = "Can inspect and stop only the configured Mattermost VM through a custom role."

  depends_on = [google_project_service.required["iam.googleapis.com"]]
}

resource "google_service_account" "action_executor" {
  account_id   = "${var.name_prefix}-action-executor"
  display_name = "NoBS Action Executor"
  description  = "Executes only organizer-approved commands; has no model, query, or gateway authority."

  depends_on = [google_project_service.required["iam.googleapis.com"]]
}

resource "google_project_iam_member" "agent_roles" {
  for_each = local.agent_project_roles

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.agent.email}"
}

resource "google_project_iam_member" "vm_roles" {
  for_each = local.vm_project_roles

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.mattermost.email}"
}

resource "google_project_iam_member" "action_executor_roles" {
  for_each = local.executor_project_roles

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.action_executor.email}"
}

resource "google_project_iam_member" "budget_guard_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.budget_guard.email}"
}

resource "google_project_iam_custom_role" "budget_guard" {
  role_id     = "nopingBudgetGuard"
  title       = "NoPing Budget Guard"
  description = "Inspect and stop the single NoPing Mattermost VM when the budget threshold is crossed."
  permissions = [
    "compute.instances.get",
    "compute.instances.stop",
  ]
}

resource "google_project_iam_member" "budget_guard_custom" {
  project = var.project_id
  role    = google_project_iam_custom_role.budget_guard.name
  member  = "serviceAccount:${google_service_account.budget_guard.email}"
}

resource "google_service_account_iam_member" "pubsub_mints_tokens" {
  service_account_id = google_service_account.pubsub_push.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"

  depends_on = [google_project_service.required["pubsub.googleapis.com"]]
}
