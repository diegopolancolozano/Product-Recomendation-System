output "repository_id"  { value = google_artifact_registry_repository.supermarket.repository_id }
output "repository_url" { value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.supermarket.repository_id}" }
output "fastapi_trigger_id" { value = var.github_connected ? google_cloudbuild_trigger.fastapi[0].trigger_id : "" }
output "nextjs_trigger_id"  { value = var.github_connected ? google_cloudbuild_trigger.nextjs[0].trigger_id : "" }
