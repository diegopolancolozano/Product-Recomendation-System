# Obtener info del proyecto (número de proyecto para IAM de GCS)
data "google_project" "project" {}

# Habilitar APIs necesarias
resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "storage.googleapis.com",
    "sqladmin.googleapis.com",
    "dataproc.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com",
    "eventarc.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}

# ── Módulos ────────────────────────────────────────────────────────────────────

module "networking" {
  source = "./modules/networking"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment

  depends_on = [google_project_service.apis]
}

module "iam" {
  source = "./modules/iam"

  project_id     = var.project_id
  project_number = data.google_project.project.number
  environment    = var.environment

  depends_on = [google_project_service.apis]
}

module "gcs" {
  source = "./modules/gcs"

  bucket_name = var.bucket_name
  region      = var.region
  environment = var.environment

  depends_on = [google_project_service.apis]
}

module "cloudsql" {
  source = "./modules/cloudsql"

  project_id        = var.project_id
  region            = var.region
  environment       = var.environment
  db_name           = var.db_name
  db_user           = var.db_user
  db_password       = var.db_password
  db_tier           = var.db_tier
  vpc_id            = module.networking.vpc_id
  vpc_connection_id = module.networking.vpc_connection_id

  depends_on = [module.networking]
}

module "dataproc" {
  source = "./modules/dataproc"

  project_id          = var.project_id
  region              = var.region
  zone                = var.zone
  environment         = var.environment
  bucket_name         = module.gcs.bucket_name
  subnet_name         = module.networking.subnet_name
  dataproc_sa_email   = module.iam.dataproc_sa_email
  master_machine_type = var.dataproc_master_type
  worker_machine_type = var.dataproc_worker_type
  worker_count        = var.dataproc_worker_count

  depends_on = [module.networking, module.iam, module.gcs]
}

# Espera 90s para que los permisos IAM de Eventarc se propaguen en GCP
resource "time_sleep" "iam_propagation" {
  create_duration = "90s"
  depends_on      = [module.iam]
}

module "cloud_functions" {
  source = "./modules/cloud_functions"

  project_id           = var.project_id
  region               = var.region
  environment          = var.environment
  bucket_name          = module.gcs.bucket_name
  functions_sa_email   = module.iam.cloud_functions_sa_email
  dataproc_cluster_name = module.dataproc.cluster_name

  depends_on = [module.dataproc, module.gcs, module.iam, time_sleep.iam_propagation]
}

module "artifact_registry" {
  source = "./modules/artifact_registry"

  project_id           = var.project_id
  region               = var.region
  environment          = var.environment
  github_owner         = var.github_owner
  github_repo          = var.github_repo
  github_branch        = var.github_branch
  cloud_build_sa_email = module.iam.cloud_build_sa_email
  github_connected     = var.github_connected

  depends_on = [module.iam, google_project_service.apis]
}

module "cloud_run" {
  source = "./modules/cloud_run"

  project_id         = var.project_id
  region             = var.region
  environment        = var.environment
  fastapi_image      = var.fastapi_image
  nextjs_image       = var.nextjs_image
  max_instances      = var.cloud_run_max_instances
  cloud_run_sa_email = module.iam.cloud_run_api_sa_email
  db_private_ip      = module.cloudsql.instance_private_ip
  db_name            = var.db_name
  db_user            = var.db_user
  db_password        = var.db_password
  bucket_name = module.gcs.bucket_name
  vpc_name    = module.networking.vpc_name

  depends_on = [module.cloudsql, module.networking, module.iam]
}
