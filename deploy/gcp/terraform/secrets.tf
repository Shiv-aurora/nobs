resource "google_secret_manager_secret" "service_signing_secret" {
  secret_id = "${var.name_prefix}-service-signing-secret"
  labels    = local.common_labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.required["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret" "postgres_password" {
  secret_id = "${var.name_prefix}-postgres-password"
  labels    = local.common_labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.required["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret" "mattermost_admin_password" {
  secret_id = "${var.name_prefix}-mattermost-admin-password"
  labels    = local.common_labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.required["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret" "demo_user_password" {
  secret_id = "${var.name_prefix}-demo-user-password"
  labels    = local.common_labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.required["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_iam_member" "agent_reads_signing_secret" {
  secret_id = google_secret_manager_secret.service_signing_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent.email}"
}
