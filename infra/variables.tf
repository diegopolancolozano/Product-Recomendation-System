variable "project_id" {
  description = "ID del proyecto GCP"
  type        = string
}

variable "region" {
  description = "Region GCP"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zona GCP para Dataproc"
  type        = string
  default     = "us-central1-a"
}

variable "db_password" {
  description = "Contrasena del usuario de Cloud SQL"
  type        = string
  sensitive   = true
}

variable "github_owner" {
  description = "Usuario u organizacion de GitHub (para el trigger de Cloud Build)"
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "Nombre del repositorio GitHub (sin el owner)"
  type        = string
  default     = "Product-Recomendation-System"
}

variable "api_service_name" {
  description = "Nombre del servicio Cloud Run del backend"
  type        = string
  default     = "supermarket-api"
}

variable "frontend_service_name" {
  description = "Nombre del servicio Cloud Run del frontend"
  type        = string
  default     = "supermarket-frontend"
}

variable "registry_repo" {
  description = "Nombre del repositorio en Artifact Registry"
  type        = string
  default     = "supermarket-analytics"
}
