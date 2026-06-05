# ── Artifact Registry — repositorio de imágenes Docker ───────────────────────
resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = var.registry_repo
  format        = "DOCKER"
  description   = "Imagenes Docker — Supermarket Analytics"

  depends_on = [google_project_service.apis]
}

# ── Cloud Run — Backend FastAPI ───────────────────────────────────────────────
resource "google_cloud_run_v2_service" "api" {
  name     = var.api_service_name
  location = var.region

  template {
    service_account = google_service_account.cloudrun_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      # Imagen placeholder para el primer terraform apply.
      # Cloud Build la reemplaza con la imagen real en el primer push a main.
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      resources {
        limits = {
          cpu    = "1"
          memory = "2Gi"
        }
        startup_cpu_boost = true
      }

      # Modo Cloud SQL (produccion) — el API lee de PostgreSQL en vez de CSV
      env {
        name  = "CLOUD_SQL_INSTANCE"
        value = google_sql_database_instance.postgres.connection_name
      }
      env {
        name  = "DB_USER"
        value = "supermarket"
      }
      env {
        name  = "DB_PASSWORD"
        value = var.db_password
      }
      # DATA_DIR solo se usa en modo local (fallback)
      env {
        name  = "DATA_DIR"
        value = "/app/DataSet/DataSet"
      }

      ports {
        container_port = 8080
      }

      startup_probe {
        http_get { path = "/api/health" }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 10
      }
    }

    timeout = "120s"
  }

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository.images,
  ]
}

# Acceso público al API (sin autenticación — para demo)
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Cloud Run — Frontend Next.js ──────────────────────────────────────────────
resource "google_cloud_run_v2_service" "frontend" {
  name     = var.frontend_service_name
  location = var.region

  template {
    service_account = google_service_account.cloudrun_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = google_cloud_run_v2_service.api.uri
      }

      ports {
        container_port = 3000
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository.images,
    google_cloud_run_v2_service.api,
  ]
}

# Acceso público al frontend
resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
