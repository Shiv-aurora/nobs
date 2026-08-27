variable "project_id" {
  description = "Existing Google Cloud project used only for the NoPing hackathon deployment."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid Google Cloud project ID."
  }
}

variable "billing_account_id" {
  description = "Billing account ID used to create the $25 project budget. Leave blank to skip budget creation."
  type        = string
  default     = ""
  sensitive   = true
}

variable "region" {
  type        = string
  description = "Google Cloud region for Cloud Run, Artifact Registry, and Model Armor."
  default     = "us-central1"
}

variable "zone" {
  type        = string
  description = "Compute Engine zone for the Mattermost VM."
  default     = "us-central1-a"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for NoPing resources."
  default     = "noping"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,20}[a-z0-9]$", var.name_prefix))
    error_message = "name_prefix must be 3-22 lowercase letters, numbers, or hyphens."
  }
}

variable "environment" {
  type        = string
  description = "Environment label."
  default     = "hackathon"
}

variable "mattermost_machine_type" {
  type        = string
  description = "Smallest planned Mattermost VM. Upgrade only after measured memory pressure."
  default     = "e2-small"

  validation {
    condition     = contains(["e2-small", "e2-medium"], var.mattermost_machine_type)
    error_message = "Use e2-small by default; e2-medium is the only approved measured-pressure upgrade."
  }
}

variable "mattermost_disk_size_gb" {
  type        = number
  description = "Standard persistent disk size for Mattermost, PostgreSQL, and plugin artifacts."
  default     = 20

  validation {
    condition     = var.mattermost_disk_size_gb >= 20 && var.mattermost_disk_size_gb <= 30
    error_message = "Disk size must remain between 20 GB and 30 GB for the hackathon cost profile."
  }
}

variable "mattermost_site_address" {
  type        = string
  description = "Caddy site address. Use :80 for a stable raw-IP demo or a hostname for managed HTTPS."
  default     = ":80"
}

variable "mattermost_image" {
  type        = string
  description = "Pinned Mattermost Team Edition image."
  default     = "mattermost/mattermost-team-edition:11.10.1"
}

variable "auto_shutdown_hour_utc" {
  type        = number
  description = "Daily UTC hour when the Mattermost VM shuts itself down. Use -1 to disable."
  default     = 6

  validation {
    condition     = var.auto_shutdown_hour_utc == -1 || (var.auto_shutdown_hour_utc >= 0 && var.auto_shutdown_hour_utc <= 23)
    error_message = "auto_shutdown_hour_utc must be -1 or an hour from 0 through 23."
  }
}

variable "deploy_agent_service" {
  type        = bool
  description = "Second-stage switch: create Cloud Run after the image and signing secret version exist."
  default     = false
}

variable "agent_image_uri" {
  type        = string
  description = "Immutable Artifact Registry image URI for the agent service."
  default     = ""
}

variable "deploy_budget_guard" {
  type        = bool
  description = "Second-stage switch: deploy the private budget guard after its image exists."
  default     = false
}

variable "budget_guard_image_uri" {
  type        = string
  description = "Immutable Artifact Registry image URI for the budget guard."
  default     = ""
}

variable "budget_guard_dry_run" {
  type        = bool
  description = "When true, log the stop action without stopping the VM. Set false after the test notification succeeds."
  default     = true
}

variable "budget_amount_usd" {
  type        = number
  description = "Maximum monthly project budget target."
  default     = 25

  validation {
    condition     = var.budget_amount_usd > 0 && var.budget_amount_usd <= 25
    error_message = "The NoPing hackathon budget must not exceed USD 25."
  }
}

variable "budget_stop_ratio" {
  type        = number
  description = "Ratio at which the budget guard stops the Mattermost VM."
  default     = 0.90

  validation {
    condition     = var.budget_stop_ratio >= 0.75 && var.budget_stop_ratio <= 1.0
    error_message = "budget_stop_ratio must be between 0.75 and 1.0."
  }
}

variable "firestore_location" {
  type        = string
  description = "Firestore database location."
  default     = "us-central1"
}

variable "create_firestore_database" {
  type        = bool
  description = "Set false if the project already has its required default Firestore database."
  default     = true
}

variable "model_armor_location" {
  type        = string
  description = "Regional Model Armor endpoint location."
  default     = "us-central1"
}

variable "model_armor_template_id" {
  type        = string
  description = "Model Armor template created by scripts/configure-model-armor.sh."
  default     = "noping-enterprise-guard"
}

variable "gemini_model" {
  type        = string
  description = "Gemini model used by Google ADK through Vertex AI."
  default     = "gemini-3.5-flash"
}

variable "gemini_location" {
  type        = string
  description = "Vertex AI endpoint location for the configured Gemini model."
  default     = "global"
}

variable "github_identity_map_json" {
  type        = string
  description = "JSON mapping GitHub logins to NoPing user IDs for signed webhook events."
  default     = "{}"
}

variable "github_repository_map_json" {
  type        = string
  description = "JSON mapping full GitHub repository names to NoPing entity ID arrays."
  default     = "{}"
}

variable "google_calendar_identity_map_json" {
  type        = string
  description = "JSON mapping approved Calendar identities to privacy-minimal NoPing availability identities."
  default     = "{}"
}

variable "labels" {
  type        = map(string)
  description = "Additional labels applied to supported resources."
  default     = {}
}
