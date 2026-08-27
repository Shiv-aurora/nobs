resource "google_billing_budget" "noping" {
  count = trimspace(var.billing_account_id) == "" ? 0 : 1

  billing_account = var.billing_account_id
  display_name    = local.budget_name

  budget_filter {
    projects        = ["projects/${data.google_project.current.number}"]
    calendar_period = "MONTH"
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.budget_amount_usd)
    }
  }

  dynamic "threshold_rules" {
    for_each = toset([0.25, 0.50, 0.75, 0.90, 1.00])
    content {
      threshold_percent = threshold_rules.value
      spend_basis       = "CURRENT_SPEND"
    }
  }

  all_updates_rule {
    pubsub_topic                   = google_pubsub_topic.budget_updates.id
    schema_version                 = "1.0"
    disable_default_iam_recipients = false
    enable_project_level_recipients = true
  }
}
