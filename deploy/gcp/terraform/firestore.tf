resource "google_firestore_database" "default" {
  count = var.create_firestore_database ? 1 : 0

  project                           = var.project_id
  name                              = "(default)"
  location_id                       = var.firestore_location
  type                              = "FIRESTORE_NATIVE"
  delete_protection_state           = "DELETE_PROTECTION_DISABLED"
  deletion_policy                   = "DELETE"
  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_DISABLED"

  depends_on = [google_project_service.required["firestore.googleapis.com"]]
}
