output "artifact_registry_repository" {
  value = google_artifact_registry_repository.noping.name
}

output "agent_image_prefix" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.noping.repository_id}/agent-service"
}

output "budget_guard_image_prefix" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.noping.repository_id}/budget-guard"
}

output "action_executor_image_prefix" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.noping.repository_id}/action-executor"
}

output "mattermost_instance_name" {
  value = google_compute_instance.mattermost.name
}

output "mattermost_external_ip" {
  value = google_compute_address.mattermost.address
}

output "mattermost_url" {
  value = var.mattermost_site_address == ":80" ? "http://${google_compute_address.mattermost.address}" : "https://${var.mattermost_site_address}"
}

output "agent_service_url" {
  value = var.deploy_agent_service ? google_cloud_run_v2_service.agent[0].uri : null
}

output "budget_guard_url" {
  value = var.deploy_budget_guard ? google_cloud_run_v2_service.budget_guard[0].uri : null
}

output "action_executor_url" {
  value = var.deploy_action_executor ? google_cloud_run_v2_service.action_executor[0].uri : null
}

output "action_commands_topic" {
  value = google_pubsub_topic.action_commands.name
}

output "service_signing_secret_id" {
  value = google_secret_manager_secret.service_signing_secret.secret_id
}

output "postgres_password_secret_id" {
  value = google_secret_manager_secret.postgres_password.secret_id
}

output "mattermost_admin_password_secret_id" {
  value = google_secret_manager_secret.mattermost_admin_password.secret_id
}

output "demo_user_password_secret_id" {
  value = google_secret_manager_secret.demo_user_password.secret_id
}

output "github_webhook_secret_id" {
  value = google_secret_manager_secret.github_webhook_secret.secret_id
}

output "google_calendar_credentials_secret_id" {
  value = google_secret_manager_secret.google_calendar_credentials.secret_id
}

output "github_identity_map_json" {
  value = var.github_identity_map_json
}

output "github_repository_map_json" {
  value = var.github_repository_map_json
}

output "google_calendar_identity_map_json" {
  value = var.google_calendar_identity_map_json
}

output "pubsub_push_service_account" {
  value = google_service_account.pubsub_push.email
}

output "mattermost_service_account" {
  value = google_service_account.mattermost.email
}

output "monthly_budget_usd" {
  value = var.budget_amount_usd
}

output "mattermost_site_address" {
  value = var.mattermost_site_address
}

output "region" {
  value = var.region
}

output "zone" {
  value = var.zone
}

output "budget_display_name" {
  value = local.budget_name
}

output "agent_service_name" {
  value = local.agent_service_name
}

output "budget_guard_service_name" {
  value = local.budget_guard_name
}

output "budget_updates_topic" {
  value = google_pubsub_topic.budget_updates.name
}
