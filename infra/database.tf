# ── Cloud SQL — PostgreSQL ────────────────────────────────────────────────────
# Dos schemas: analitica (metricas KPI) y ml_resultados (clusters + reglas)
# Tier db-f1-micro es el mas economico para demo/desarrollo

resource "google_sql_database_instance" "postgres" {
  name             = "supermarket-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_size         = 10
    disk_autoresize   = false

    backup_configuration {
      enabled = false
    }

    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "all-demo"
        value = "0.0.0.0/0"
      }
    }
  }

  deletion_protection = false
  depends_on          = [google_project_service.apis]
}

resource "google_sql_database" "analitica" {
  name     = "analitica"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_database" "ml_resultados" {
  name     = "ml_resultados"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app_user" {
  name     = "supermarket"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}
