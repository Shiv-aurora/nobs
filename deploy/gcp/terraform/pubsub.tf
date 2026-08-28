resource "google_pubsub_topic" "work_events" {
  name   = "${var.name_prefix}-work-events"
  labels = local.common_labels

  message_retention_duration = "86400s"

  depends_on = [google_project_service.required["pubsub.googleapis.com"]]
}

resource "google_pubsub_topic" "work_events_dlq" {
  name   = "${var.name_prefix}-work-events-dlq"
  labels = local.common_labels

  message_retention_duration = "604800s"

  depends_on = [google_project_service.required["pubsub.googleapis.com"]]
}

resource "google_pubsub_topic" "budget_updates" {
  name   = "${var.name_prefix}-budget-updates"
  labels = local.common_labels

  message_retention_duration = "604800s"

  depends_on = [google_project_service.required["pubsub.googleapis.com"]]
}

resource "google_pubsub_topic_iam_member" "billing_budget_publishes_updates" {
  topic = google_pubsub_topic.budget_updates.name
  role  = "roles/pubsub.publisher"
  # The Budget API grants this Google-managed system principal when a topic is
  # connected. Manage the same narrow binding so subsequent plans verify it.
  member = "serviceAccount:billing-budget-alert@system.gserviceaccount.com"

  depends_on = [google_billing_budget.noping]
}

resource "google_pubsub_topic_iam_member" "vm_publishes_work_events" {
  topic  = google_pubsub_topic.work_events.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.mattermost.email}"
}

resource "google_pubsub_subscription" "work_events_push" {
  count = var.deploy_agent_service ? 1 : 0

  name   = "${var.name_prefix}-work-events-push"
  topic  = google_pubsub_topic.work_events.id
  labels = local.common_labels

  ack_deadline_seconds       = 120
  message_retention_duration = "86400s"
  retain_acked_messages      = false

  expiration_policy {
    ttl = "2678400s"
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.work_events_dlq.id
    max_delivery_attempts = 5
  }

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.agent[0].uri}/v1/events/pubsub"

    oidc_token {
      service_account_email = google_service_account.pubsub_push.email
      audience              = local.agent_service_audience
    }

    attributes = {
      x-goog-version = "v1"
    }
  }

  depends_on = [
    google_cloud_run_v2_service_iam_member.pubsub_invokes_agent,
    google_service_account_iam_member.pubsub_mints_tokens,
  ]
}

resource "google_pubsub_subscription" "work_events_dlq_inspection" {
  name   = "${var.name_prefix}-work-events-dlq-inspection"
  topic  = google_pubsub_topic.work_events_dlq.id
  labels = local.common_labels

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"
  retain_acked_messages      = false

  expiration_policy {
    ttl = "2678400s"
  }
}

resource "google_pubsub_topic_iam_member" "pubsub_service_publishes_dlq" {
  topic  = google_pubsub_topic.work_events_dlq.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription_iam_member" "pubsub_service_reads_source" {
  count = var.deploy_agent_service ? 1 : 0

  subscription = google_pubsub_subscription.work_events_push[0].name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription" "budget_guard_push" {
  count = var.deploy_budget_guard ? 1 : 0

  name   = "${var.name_prefix}-budget-guard-push"
  topic  = google_pubsub_topic.budget_updates.id
  labels = local.common_labels

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"

  expiration_policy {
    ttl = "2678400s"
  }

  retry_policy {
    minimum_backoff = "30s"
    maximum_backoff = "600s"
  }

  push_config {
    push_endpoint = google_cloud_run_v2_service.budget_guard[0].uri

    oidc_token {
      service_account_email = google_service_account.pubsub_push.email
      audience              = local.budget_guard_audience
    }
  }

  depends_on = [
    google_cloud_run_v2_service_iam_member.pubsub_invokes_budget_guard,
    google_service_account_iam_member.pubsub_mints_tokens,
  ]
}
