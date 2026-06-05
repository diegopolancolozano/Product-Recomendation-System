# ── Cloud Build Trigger ────────────────────────────────────────────────────────
# El trigger de GitHub requiere conectar el repositorio manualmente en la consola
# ANTES de que Terraform pueda crearlo.
#
# Pasos:
#   1. Ir a GCP Console → Cloud Build → Repositorios → Conectar repositorio
#   2. Seleccionar GitHub → autorizar → elegir Product-Recomendation-System
#   3. Descomentar el recurso de abajo y ejecutar terraform apply de nuevo
#
# resource "google_cloudbuild_trigger" "deploy" {
#   name        = "supermarket-deploy"
#   description = "Construye y despliega API + frontend en cada push a main"
#   location    = var.region
#
#   github {
#     owner = var.github_owner
#     name  = var.github_repo
#     push  { branch = "^main$" }
#   }
#
#   filename = "cloudbuild.yaml"
#
#   substitutions = {
#     _REGION        = var.region
#     _REPO          = var.registry_repo
#     _API_SERVICE   = var.api_service_name
#     _FRONT_SERVICE = var.frontend_service_name
#     _API_URL       = google_cloud_run_v2_service.api.uri
#   }
# }
