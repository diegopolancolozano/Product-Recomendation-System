resource "google_artifact_registry_repository" "supermarket" {
  location      = var.region
  repository_id = "${var.environment}-supermarket"
  format        = "DOCKER"
  description   = "Imágenes Docker para el sistema de recomendación de supermercado"

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

# Trigger Cloud Build — FastAPI
# IMPORTANTE: Conectar GitHub primero en:
# https://console.cloud.google.com/cloud-build/triggers/connect
# Luego cambiar github_connected = true en variables y re-aplicar.
resource "google_cloudbuild_trigger" "fastapi" {
  count = var.github_connected ? 1 : 0
  name            = "${var.environment}-build-fastapi"
  description     = "Build y push de imagen FastAPI al Artifact Registry"
  location        = var.region
  service_account = "projects/${var.project_id}/serviceAccounts/${var.cloud_build_sa_email}"

  github {
    owner = var.github_owner
    name  = var.github_repo

    push {
      branch = "^${var.github_branch}$"
    }
  }

  included_files = ["api/**"]

  build {
    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "build",
        "-t", "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.supermarket.repository_id}/fastapi:$COMMIT_SHA",
        "-t", "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.supermarket.repository_id}/fastapi:latest",
        "./api",
      ]
    }

    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "push", "--all-tags",
        "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.supermarket.repository_id}/fastapi",
      ]
    }

    step {
      name       = "gcr.io/google.com/cloudsdktool/cloud-sdk"
      entrypoint = "gcloud"
      args = [
        "run", "deploy", "${var.environment}-fastapi",
        "--image", "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.supermarket.repository_id}/fastapi:$COMMIT_SHA",
        "--region", var.region,
        "--platform", "managed",
        "--quiet",
      ]
    }

    options {
      logging = "CLOUD_LOGGING_ONLY"
    }
  }
}

# Trigger Cloud Build — Next.js Frontend
resource "google_cloudbuild_trigger" "nextjs" {
  count = var.github_connected ? 1 : 0
  name            = "${var.environment}-build-nextjs"
  description     = "Build y push de imagen Next.js al Artifact Registry"
  location        = var.region
  service_account = "projects/${var.project_id}/serviceAccounts/${var.cloud_build_sa_email}"

  github {
    owner = var.github_owner
    name  = var.github_repo

    push {
      branch = "^${var.github_branch}$"
    }
  }

  included_files = ["frontend/**"]

  build {
    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "build",
        "-t", "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.supermarket.repository_id}/nextjs:$COMMIT_SHA",
        "-t", "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.supermarket.repository_id}/nextjs:latest",
        "./frontend",
      ]
    }

    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "push", "--all-tags",
        "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.supermarket.repository_id}/nextjs",
      ]
    }

    step {
      name       = "gcr.io/google.com/cloudsdktool/cloud-sdk"
      entrypoint = "gcloud"
      args = [
        "run", "deploy", "${var.environment}-nextjs",
        "--image", "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.supermarket.repository_id}/nextjs:$COMMIT_SHA",
        "--region", var.region,
        "--platform", "managed",
        "--quiet",
      ]
    }

    options {
      logging = "CLOUD_LOGGING_ONLY"
    }
  }
}
