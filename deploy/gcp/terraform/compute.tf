resource "google_compute_instance" "mattermost" {
  name         = local.mattermost_name
  machine_type = var.mattermost_machine_type
  zone         = var.zone
  tags         = ["${var.name_prefix}-mattermost"]
  labels       = local.common_labels

  allow_stopping_for_update = true
  deletion_protection       = false

  boot_disk {
    initialize_params {
      image  = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2404-lts-amd64"
      size   = var.mattermost_disk_size_gb
      type   = "pd-standard"
      labels = local.common_labels
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.noping.id
    access_config {
      nat_ip = google_compute_address.mattermost.address
    }
  }

  service_account {
    email  = google_service_account.mattermost.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  metadata = {
    enable-oslogin = "TRUE"
  }

  metadata_startup_script = templatefile("${path.module}/templates/vm-startup.sh.tftpl", {
    auto_shutdown_hour_utc = var.auto_shutdown_hour_utc
  })

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    provisioning_model  = "STANDARD"
  }

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  lifecycle {
    precondition {
      condition     = contains(["e2-small", "e2-medium"], var.mattermost_machine_type)
      error_message = "NoPing intentionally constrains the VM to e2-small/e2-medium."
    }
  }

  depends_on = [
    google_compute_firewall.web,
    google_compute_firewall.iap_ssh,
  ]
}
