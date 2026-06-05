output "frontend_url" {
  description = "URL publica del dashboard (Next.js en Cloud Run)"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "api_url" {
  description = "URL publica del backend (FastAPI en Cloud Run)"
  value       = google_cloud_run_v2_service.api.uri
}

output "api_docs_url" {
  description = "Swagger UI del backend"
  value       = "${google_cloud_run_v2_service.api.uri}/docs"
}

output "bucket_name" {
  description = "Bucket de Cloud Storage (depositar CSV en /raw/)"
  value       = google_storage_bucket.data.name
}

output "artifact_registry" {
  description = "URL base del repositorio Docker en Artifact Registry"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.registry_repo}"
}

output "db_connection_name" {
  description = "Connection name de Cloud SQL (para Cloud SQL Auth Proxy)"
  value       = google_sql_database_instance.postgres.connection_name
}

output "dataproc_cluster" {
  description = "Nombre del cluster Dataproc"
  value       = google_dataproc_cluster.spark.name
}

output "docker_push_commands" {
  description = "Comandos para autenticar Docker con Artifact Registry"
  value       = "gcloud auth configure-docker ${var.region}-docker.pkg.dev"
}
