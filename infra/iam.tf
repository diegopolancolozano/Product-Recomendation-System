# ── Service Accounts propios ──────────────────────────────────────────────────

resource "google_service_account" "functions_sa" {
  account_id   = "supermarket-functions"
  display_name = "Supermarket Cloud Functions SA"
  depends_on   = [google_project_service.apis]
}

resource "google_service_account" "dataproc_sa" {
  account_id   = "supermarket-dataproc"
  display_name = "Supermarket Dataproc SA"
  depends_on   = [google_project_service.apis]
}

resource "google_service_account" "cloudrun_sa" {
  account_id   = "supermarket-cloudrun"
  display_name = "Supermarket Cloud Run SA"
  depends_on   = [google_project_service.apis]
}

# ── Service Identities de GCP (creadas explicitamente para evitar race conditions) ──
# google_project_service_identity garantiza que el SA existe antes de asignarle roles.

resource "google_project_service_identity" "eventarc" {
  provider   = google-beta
  project    = var.project_id
  service    = "eventarc.googleapis.com"
  depends_on = [google_project_service.apis]
}

# GCS tiene su propio data source — no usa google_project_service_identity
data "google_storage_project_service_account" "gcs_account" {
  project    = var.project_id
  depends_on = [google_project_service.apis]
}

resource "google_project_service_identity" "pubsub" {
  provider   = google-beta
  project    = var.project_id
  service    = "pubsub.googleapis.com"
  depends_on = [google_project_service.apis]
}

resource "google_project_service_identity" "cloudfunctions" {
  provider   = google-beta
  project    = var.project_id
  service    = "cloudfunctions.googleapis.com"
  depends_on = [google_project_service.apis]
}

# ── Roles para Eventarc Service Agent ────────────────────────────────────────

resource "google_project_iam_member" "eventarc_agent" {
  project = var.project_id
  role    = "roles/eventarc.serviceAgent"
  member  = "serviceAccount:${google_project_service_identity.eventarc.email}"
}

# Eventarc necesita poder invocar Cloud Functions (Cloud Run subyacente)
resource "google_project_iam_member" "eventarc_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_project_service_identity.eventarc.email}"
}

# GCS necesita publicar en Pub/Sub para disparar el trigger de Eventarc
resource "google_project_iam_member" "gcs_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"
}

# ── Roles para Cloud Functions SA ────────────────────────────────────────────

resource "google_project_iam_member" "functions_dataproc" {
  project = var.project_id
  role    = "roles/dataproc.editor"
  member  = "serviceAccount:${google_service_account.functions_sa.email}"
}

resource "google_project_iam_member" "functions_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.functions_sa.email}"
}

resource "google_project_iam_member" "functions_storage" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.functions_sa.email}"
}

# Necesario para que el SA reciba eventos de Eventarc (GCS trigger)
resource "google_project_iam_member" "functions_eventarc_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.functions_sa.email}"
}

# ── Roles para Dataproc SA ────────────────────────────────────────────────────

resource "google_project_iam_member" "dataproc_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.dataproc_sa.email}"
}

resource "google_project_iam_member" "dataproc_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.dataproc_sa.email}"
}

resource "google_project_iam_member" "dataproc_worker" {
  project = var.project_id
  role    = "roles/dataproc.worker"
  member  = "serviceAccount:${google_service_account.dataproc_sa.email}"
}

# ── Roles para Cloud Run SA ───────────────────────────────────────────────────

resource "google_project_iam_member" "cloudrun_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloudrun_sa.email}"
}

resource "google_project_iam_member" "cloudrun_storage" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.cloudrun_sa.email}"
}

# ── Cloud Build — instrucciones para configurar manualmente ──────────────────
# Ejecutar DESPUES del primer terraform apply:
#
#   PROJECT_NUMBER=$(gcloud projects describe distribuidosrecomendacion --format='value(projectNumber)')
#   gcloud projects add-iam-policy-binding distribuidosrecomendacion \
#     --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
#     --role="roles/run.admin"
#   gcloud projects add-iam-policy-binding distribuidosrecomendacion \
#     --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
#     --role="roles/iam.serviceAccountUser"

data "google_project" "project" {
  project_id = var.project_id
}
