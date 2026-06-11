# VPC Serverless Connector — se crea primero para que los servicios lo referencien
resource "google_vpc_access_connector" "connector" {
  name          = "${var.environment}-vpc-connector"
  region        = var.region
  network       = var.vpc_name
  ip_cidr_range = "10.8.0.0/28"

  min_throughput = 200
  max_throughput = 300
}

# ── FastAPI Backend ────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "fastapi" {
  name     = "${var.environment}-fastapi"
  location = var.region

  template {
    service_account = var.cloud_run_sa_email

    scaling {
      min_instance_count = 0
      max_instance_count = var.max_instances
    }

    containers {
      image = var.fastapi_image

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      env {
        name  = "DB_HOST"
        value = var.db_private_ip
      }
      env {
        name  = "DB_NAME"
        value = var.db_name
      }
      env {
        name  = "DB_USER"
        value = var.db_user
      }
      env {
        name  = "DB_PASSWORD"
        value = var.db_password
      }
      env {
        name  = "GCS_BUCKET"
        value = var.bucket_name
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
    }

    # Referencia directa al connector creado en este módulo
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }

  depends_on = [google_vpc_access_connector.connector]
}

# Acceso público al endpoint de FastAPI
resource "google_cloud_run_v2_service_iam_member" "fastapi_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.fastapi.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Next.js Frontend ───────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "nextjs" {
  name     = "${var.environment}-nextjs"
  location = var.region

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = var.max_instances
    }

    containers {
      image = var.nextjs_image

      ports {
        container_port = 3000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = google_cloud_run_v2_service.fastapi.uri
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
    }
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

# Acceso público al Frontend
resource "google_cloud_run_v2_service_iam_member" "nextjs_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.nextjs.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
