output "fastapi_url"       { value = google_cloud_run_v2_service.fastapi.uri }
output "nextjs_url"        { value = google_cloud_run_v2_service.nextjs.uri }
output "vpc_connector_id"  { value = google_vpc_access_connector.connector.id }
