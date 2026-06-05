# ── Cloud Storage — Bucket principal ─────────────────────────────────────────
# Prefijos usados:
#   /raw      → CSV de transacciones (entrada)
#   /models   → artefactos ML (salida de Dataproc)
#   /tmp      → staging de Spark
#   /functions → codigo fuente de Cloud Functions

resource "google_storage_bucket" "data" {
  name                        = "${var.project_id}-supermarket-data"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  lifecycle_rule {
    condition { age = 90 }
    action    { type = "Delete" }
  }

  depends_on = [google_project_service.apis]
}

# Carpetas virtuales (objetos vacios que actuan como directorios)
resource "google_storage_bucket_object" "prefix_raw" {
  name    = "raw/.keep"
  bucket  = google_storage_bucket.data.name
  content = " "
}

resource "google_storage_bucket_object" "prefix_models" {
  name    = "models/.keep"
  bucket  = google_storage_bucket.data.name
  content = " "
}

resource "google_storage_bucket_object" "prefix_tmp" {
  name    = "tmp/.keep"
  bucket  = google_storage_bucket.data.name
  content = " "
}

# Codigo fuente de la Cloud Function
data "archive_file" "trigger_source" {
  type        = "zip"
  source_dir  = "${path.module}/../cloud_functions/trigger"
  output_path = "${path.module}/trigger.zip"
}

resource "google_storage_bucket_object" "trigger_source" {
  name   = "functions/trigger-${data.archive_file.trigger_source.output_md5}.zip"
  bucket = google_storage_bucket.data.name
  source = data.archive_file.trigger_source.output_path
}

# ── Jobs de Spark (subidos al bucket para que Dataproc los ejecute) ────────────
resource "google_storage_bucket_object" "spark_etl" {
  name   = "spark/01_etl.py"
  bucket = google_storage_bucket.data.name
  source = "${path.module}/../spark_jobs/01_etl.py"
}

resource "google_storage_bucket_object" "spark_ml" {
  name   = "spark/02_ml.py"
  bucket = google_storage_bucket.data.name
  source = "${path.module}/../spark_jobs/02_ml.py"
}

resource "google_storage_bucket_object" "spark_aggregations" {
  name   = "spark/03_aggregations.py"
  bucket = google_storage_bucket.data.name
  source = "${path.module}/../spark_jobs/03_aggregations.py"
}

# ── Scripts SQL de inicializacion de la base de datos ────────────────────────
resource "google_storage_bucket_object" "sql_analitica" {
  name   = "sql/init_analitica.sql"
  bucket = google_storage_bucket.data.name
  source = "${path.module}/../db/init_analitica.sql"
}

resource "google_storage_bucket_object" "sql_ml" {
  name   = "sql/init_ml_resultados.sql"
  bucket = google_storage_bucket.data.name
  source = "${path.module}/../db/init_ml_resultados.sql"
}
