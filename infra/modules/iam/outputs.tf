output "dataproc_sa_email"        { value = google_service_account.dataproc.email }
output "cloud_functions_sa_email" { value = google_service_account.cloud_functions.email }
output "cloud_run_api_sa_email"   { value = google_service_account.cloud_run_api.email }
output "cloud_build_sa_email"     { value = google_service_account.cloud_build.email }
