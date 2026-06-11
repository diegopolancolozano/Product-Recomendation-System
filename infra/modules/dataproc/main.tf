resource "google_dataproc_cluster" "main" {
  name   = "${var.environment}-supermarket-spark"
  region = var.region

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }

  cluster_config {
    staging_bucket = var.bucket_name

    gce_cluster_config {
      zone            = var.zone
      subnetwork      = var.subnet_name
      service_account = var.dataproc_sa_email

      service_account_scopes = [
        "https://www.googleapis.com/auth/cloud-platform",
      ]

      internal_ip_only = true

      metadata = {
        "enable-oslogin" = "true"
      }
    }

    master_config {
      num_instances = 1
      machine_type  = var.master_machine_type

      disk_config {
        boot_disk_type    = "pd-ssd"
        boot_disk_size_gb = 50
      }
    }

    worker_config {
      num_instances = var.worker_count
      machine_type  = var.worker_machine_type

      disk_config {
        boot_disk_type    = "pd-standard"
        boot_disk_size_gb = 50
        num_local_ssds    = 0
      }
    }

    software_config {
      image_version = "2.1-debian11"

      override_properties = {
        "dataproc:dataproc.allow.zero.workers" = "false"
        "spark:spark.sql.adaptive.enabled"      = "true"
        "spark:spark.dynamicAllocation.enabled" = "false"
      }

      optional_components = ["JUPYTER"]
    }

    endpoint_config {
      enable_http_port_access = false
    }
  }
}

# Job de ejemplo: ETL principal (se puede invocar vía Cloud Functions)
resource "google_dataproc_job" "etl_template" {
  region = var.region

  placement {
    cluster_name = google_dataproc_cluster.main.name
  }

  pyspark_config {
    main_python_file_uri = "gs://${var.bucket_name}/spark-jobs/etl_main.py"

    args = [
      "--input",  "gs://${var.bucket_name}/raw/transactions/",
      "--output", "gs://${var.bucket_name}/processed/",
    ]

    properties = {
      "spark.executor.memory" = "4g"
      "spark.driver.memory"   = "2g"
    }
  }

  lifecycle {
    ignore_changes = [placement]
  }
}
