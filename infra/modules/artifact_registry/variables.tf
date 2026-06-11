variable "project_id"           { type = string }
variable "region"               { type = string }
variable "environment"          { type = string }
variable "github_owner"         { type = string }
variable "github_repo"          { type = string }
variable "github_branch"        { type = string }
variable "cloud_build_sa_email" { type = string }
variable "github_connected" {
  type        = bool
  default     = false
  description = "Pon en true solo después de conectar GitHub en la consola de Cloud Build"
}
