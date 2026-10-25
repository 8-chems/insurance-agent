output "api_url" { value = google_cloud_run_v2_service.api.uri }
output "ingest_url" { value = google_cloud_run_v2_service.ingest.uri }
output "registry" { value = "${var.region}-docker.pkg.dev/${var.project_id}/agent" }
output "api_service_account" { value = google_service_account.api.email }
output "ingest_service_account" { value = google_service_account.ingest.email }
