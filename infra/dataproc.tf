resource "google_dataproc_cluster" "spark" {
  name   = "supermarket-spark"
  region = var.region

  cluster_config {
    # Cluster de un solo nodo (master sin workers) — suficiente para demo
    # y evita errores de cuota de IPs en proyectos nuevos.
    # Para produccion, cambiar num_instances en worker_config a 2+
    master_config {
      num_instances = 1
      machine_type  = "n1-standard-4"

      disk_config {
        boot_disk_type    = "pd-standard"
        boot_disk_size_gb = 100
      }
    }

    worker_config {
      num_instances = 0
    }

    software_config {
      image_version       = "2.1-debian11"
      optional_components = ["JUPYTER"]

      override_properties = {
        "dataproc:dataproc.allow.zero.workers" = "true"
      }
    }

    gce_cluster_config {
      zone                   = var.zone
      service_account        = google_service_account.dataproc_sa.email
      service_account_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    }

    staging_bucket = google_storage_bucket.data.name
  }

  depends_on = [
    google_project_service.apis,
    google_project_iam_member.dataproc_worker,
    google_project_iam_member.dataproc_storage,
  ]
}
