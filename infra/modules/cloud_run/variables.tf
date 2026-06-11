variable "project_id"        { type = string }
variable "region"            { type = string }
variable "environment"       { type = string }
variable "fastapi_image"     { type = string }
variable "nextjs_image"      { type = string }
variable "max_instances"     { type = number }
variable "cloud_run_sa_email" { type = string }
variable "db_private_ip"     { type = string }
variable "db_name"           { type = string }
variable "db_user"           { type = string }
variable "db_password" {
  type      = string
  sensitive = true
}
variable "bucket_name"       { type = string }
variable "vpc_name" { type = string }
