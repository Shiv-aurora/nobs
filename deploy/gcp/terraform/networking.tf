resource "google_compute_network" "noping" {
  name                    = "${var.name_prefix}-network"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  depends_on = [google_project_service.required["compute.googleapis.com"]]
}

resource "google_compute_subnetwork" "noping" {
  name                     = "${var.name_prefix}-subnet"
  ip_cidr_range            = "10.42.0.0/24"
  region                   = var.region
  network                  = google_compute_network.noping.id
  private_ip_google_access = true
}

resource "google_compute_address" "mattermost" {
  name   = "${var.name_prefix}-mattermost-ip"
  region = var.region
  labels = local.common_labels

  depends_on = [google_project_service.required["compute.googleapis.com"]]
}

resource "google_compute_firewall" "web" {
  name    = "${var.name_prefix}-allow-web"
  network = google_compute_network.noping.name

  direction     = "INGRESS"
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["${var.name_prefix}-mattermost"]

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
}

resource "google_compute_firewall" "iap_ssh" {
  name    = "${var.name_prefix}-allow-iap-ssh"
  network = google_compute_network.noping.name

  direction     = "INGRESS"
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["${var.name_prefix}-mattermost"]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
