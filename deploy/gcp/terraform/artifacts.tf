resource "google_artifact_registry_repository" "noping" {
  location      = var.region
  repository_id = "${var.name_prefix}-containers"
  description   = "NoPing Cloud Run images; retention intentionally constrained for the hackathon."
  format        = "DOCKER"
  mode          = "STANDARD_REPOSITORY"
  labels        = local.common_labels

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "delete-untagged-after-seven-days"
    action = "DELETE"

    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s"
    }
  }

  cleanup_policies {
    id     = "keep-three-recent-versions"
    action = "KEEP"

    most_recent_versions {
      keep_count = 3
    }
  }

  depends_on = [google_project_service.required["artifactregistry.googleapis.com"]]
}
