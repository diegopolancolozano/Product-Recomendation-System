resource "google_storage_bucket" "main" {
  name          = var.bucket_name
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

# Carpetas lógicas dentro del bucket
resource "google_storage_bucket_object" "folders" {
  for_each = toset([
    "raw/transactions/",
    "raw/products/",
    "processed/",
    "models/kmeans/",
    "models/recommender/",
    "artifacts/",
    "spark-jobs/",
  ])

  bucket  = google_storage_bucket.main.name
  name    = each.value
  content = " "
}
