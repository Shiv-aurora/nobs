resource "google_cloud_run_v2_service" "agent" {
  count = var.deploy_agent_service ? 1 : 0

  name                = local.agent_service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false
  labels              = local.common_labels
  custom_audiences    = [local.agent_service_audience]

  scaling {
    min_instance_count = 0
    max_instance_count = 1
  }

  template {
    service_account                  = google_service_account.agent.email
    timeout                          = "120s"
    max_instance_request_concurrency = 4
    execution_environment            = "EXECUTION_ENVIRONMENT_GEN2"
    labels                           = local.common_labels

    containers {
      name  = "agent-service"
      image = var.agent_image_uri

      ports {
        name           = "http1"
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = false
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.gemini_location
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "TRUE"
      }
      env {
        name  = "NOPING_DEMO_MODE"
        value = "false"
      }
      env {
        name  = "NOPING_AI_ENABLED"
        value = "true"
      }
      env {
        name  = "NOPING_PERSISTENCE_BACKEND"
        value = "firestore"
      }
      env {
        name  = "NOPING_FIRESTORE_DATABASE"
        value = "(default)"
      }
      env {
        name  = "NOPING_ORGANIZATION_ID"
        value = "acme"
      }
      env {
        name  = "NOPING_GEMINI_MODEL"
        value = var.gemini_model
      }
      env {
        name  = "NOPING_PUBSUB_PUSH_AUDIENCE"
        value = local.agent_service_audience
      }
      env {
        name  = "NOPING_PUBSUB_PUSH_SERVICE_ACCOUNT"
        value = google_service_account.pubsub_push.email
      }
      env {
        name  = "NOPING_MODEL_ARMOR_ENABLED"
        value = "true"
      }
      env {
        name  = "NOPING_MODEL_ARMOR_LOCATION"
        value = var.model_armor_location
      }
      env {
        name  = "NOPING_MODEL_ARMOR_TEMPLATE_ID"
        value = var.model_armor_template_id
      }
      env {
        name  = "NOPING_MODEL_ARMOR_FAIL_CLOSED"
        value = "true"
      }
      env {
        name  = "NOPING_MAX_USER_PER_MINUTE"
        value = "3"
      }
      env {
        name  = "NOPING_MAX_USER_PER_HOUR"
        value = "20"
      }
      env {
        name  = "NOPING_MAX_USER_PER_DAY"
        value = "20"
      }
      env {
        name  = "NOPING_MAX_ORG_PER_MINUTE"
        value = "10"
      }
      env {
        name  = "NOPING_MAX_ORG_PER_DAY"
        value = "60"
      }
      env {
        name  = "NOPING_MAX_CONCURRENT_RUNS"
        value = "2"
      }
      env {
        name  = "NOPING_MODEL_MAX_CALLS_PER_QUERY"
        value = "4"
      }
      env {
        name  = "NOPING_MODEL_MAX_INPUT_TOKENS_PER_QUERY"
        value = "24000"
      }
      env {
        name  = "NOPING_MODEL_MAX_OUTPUT_TOKENS_PER_QUERY"
        value = "2400"
      }
      env {
        name  = "NOPING_MODEL_MAX_CALLS_PER_DAY"
        value = "200"
      }
      env {
        name  = "NOPING_MODEL_MAX_INPUT_TOKENS_PER_DAY"
        value = "1000000"
      }
      env {
        name  = "NOPING_MODEL_MAX_OUTPUT_TOKENS_PER_DAY"
        value = "100000"
      }
      env {
        name  = "NOPING_LOG_LEVEL"
        value = "INFO"
      }
      env {
        name  = "OTEL_SERVICE_NAME"
        value = "noping-agent-service"
      }
      env {
        name = "NOPING_SERVICE_SIGNING_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.service_signing_secret.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        initial_delay_seconds = 2
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 12

        http_get {
          path = "/healthz"
          port = 8080
        }
      }

      liveness_probe {
        initial_delay_seconds = 5
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3

        http_get {
          path = "/healthz"
          port = 8080
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  lifecycle {
    precondition {
      condition     = trimspace(var.agent_image_uri) != ""
      error_message = "agent_image_uri must be an immutable Artifact Registry image before deploy_agent_service=true."
    }
  }

  depends_on = [
    google_project_iam_member.agent_roles,
    google_secret_manager_secret_iam_member.agent_reads_signing_secret,
  ]
}

resource "google_cloud_run_v2_service" "budget_guard" {
  count = var.deploy_budget_guard ? 1 : 0

  name                = local.budget_guard_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false
  labels              = local.common_labels
  custom_audiences    = [local.budget_guard_audience]

  scaling {
    min_instance_count = 0
    max_instance_count = 1
  }

  template {
    service_account                  = google_service_account.budget_guard.email
    timeout                          = "30s"
    max_instance_request_concurrency = 1
    execution_environment            = "EXECUTION_ENVIRONMENT_GEN2"
    labels                           = local.common_labels

    containers {
      name  = "budget-guard"
      image = var.budget_guard_image_uri

      ports {
        name           = "http1"
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = false
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "BUDGET_GUARD_ZONE"
        value = var.zone
      }
      env {
        name  = "BUDGET_GUARD_INSTANCE"
        value = google_compute_instance.mattermost.name
      }
      env {
        name  = "BUDGET_GUARD_EXPECTED_BUDGET"
        value = local.budget_name
      }
      env {
        name  = "BUDGET_GUARD_TRIGGER_RATIO"
        value = tostring(var.budget_stop_ratio)
      }
      env {
        name  = "BUDGET_GUARD_DRY_RUN"
        value = tostring(var.budget_guard_dry_run)
      }

      startup_probe {
        initial_delay_seconds = 1
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 6

        http_get {
          path = "/healthz"
          port = 8080
        }
      }

      liveness_probe {
        timeout_seconds   = 3
        period_seconds    = 30
        failure_threshold = 3

        http_get {
          path = "/healthz"
          port = 8080
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  lifecycle {
    precondition {
      condition     = trimspace(var.budget_guard_image_uri) != ""
      error_message = "budget_guard_image_uri must be an immutable Artifact Registry image before deploy_budget_guard=true."
    }
  }

  depends_on = [google_project_iam_member.budget_guard_custom]
}

resource "google_cloud_run_v2_service_iam_member" "mattermost_invokes_agent" {
  count = var.deploy_agent_service ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_service.agent[0].location
  name     = google_cloud_run_v2_service.agent[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.mattermost.email}"
}

resource "google_cloud_run_v2_service_iam_member" "pubsub_invokes_agent" {
  count = var.deploy_agent_service ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_service.agent[0].location
  name     = google_cloud_run_v2_service.agent[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_push.email}"
}

resource "google_cloud_run_v2_service_iam_member" "pubsub_invokes_budget_guard" {
  count = var.deploy_budget_guard ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_service.budget_guard[0].location
  name     = google_cloud_run_v2_service.budget_guard[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_push.email}"
}
