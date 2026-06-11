# Genera el ZIP automáticamente desde el código fuente Python
data "archive_file" "function_source" {
  type        = "zip"
  source_dir  = "${path.module}/source"
  output_path = "${path.module}/source/trigger_dataproc.zip"
}

# Sube el ZIP al bucket
resource "google_storage_bucket_object" "function_source" {
  name   = "functions/trigger_dataproc_${data.archive_file.function_source.output_md5}.zip"
  bucket = var.bucket_name
  source = data.archive_file.function_source.output_path
}

# Cloud Functions gen1 — trigger GCS nativo (sin Eventarc)
resource "google_cloudfunctions_function" "gcs_trigger" {
  name        = "${var.environment}-gcs-dataproc-trigger"
  description = "Lanza job Dataproc cuando llega un CSV nuevo al bucket"
  runtime     = "python311"
  region      = var.region

  available_memory_mb   = 256
  timeout               = 300
  entry_point           = "trigger_dataproc_job"
  service_account_email = var.functions_sa_email

  source_archive_bucket = var.bucket_name
  source_archive_object = google_storage_bucket_object.function_source.name

  # Trigger nativo de GCS — no requiere Eventarc
  event_trigger {
    event_type = "google.storage.object.finalize"
    resource   = var.bucket_name

    failure_policy {
      retry = true
    }
  }

  environment_variables = {
    GCP_PROJECT      = var.project_id
    DATAPROC_REGION  = var.region
    DATAPROC_CLUSTER = var.dataproc_cluster_name
    GCS_BUCKET       = var.bucket_name
  }
}
