resource "google_sql_database_instance" "main" {
  name             = "${var.environment}-supermarket-pg"
  database_version = "POSTGRES_15"
  region           = var.region

  depends_on = [var.vpc_connection_id]

  settings {
    tier              = var.db_tier
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"

    disk_autoresize       = true
    disk_autoresize_limit = 100
    disk_size             = 20
    disk_type             = "PD_SSD"

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = var.vpc_id
      enable_private_path_for_google_cloud_services = true
    }

    backup_configuration {
      enabled            = true
      start_time         = "03:00"
      binary_log_enabled = false

      backup_retention_settings {
        retained_backups = 7
      }
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }

    insights_config {
      query_insights_enabled = true
    }
  }

  deletion_protection = var.environment == "prod"
}

resource "google_sql_database" "analytics" {
  name     = var.db_name
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "analytics_user" {
  name     = var.db_user
  instance = google_sql_database_instance.main.name
  password = var.db_password
}
