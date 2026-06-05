# ── Cloud Functions Gen2 — Trigger de pipeline ETL → ML → Aggregations ────────
#
# La Cloud Function se despliega con gcloud despues del terraform apply
# porque requiere que el Cloud Build SA ya exista con los permisos necesarios.
#
# Comando para desplegar (ejecutar desde la raiz del proyecto):
#
#   gcloud functions deploy supermarket-trigger \
#     --gen2 \
#     --region=us-central1 \
#     --runtime=python311 \
#     --entry-point=main \
#     --source=cloud_functions/trigger \
#     --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
#     --trigger-event-filters="bucket=distribuidosrecomendacion-supermarket-data" \
#     --service-account=supermarket-functions@distribuidosrecomendacion.iam.gserviceaccount.com \
#     --set-env-vars="GCP_PROJECT=distribuidosrecomendacion,REGION=us-central1,DATAPROC_CLUSTER=supermarket-spark,DB_HOST=$(terraform output -raw db_connection_name | cut -d: -f3),DB_PASSWORD=TU_PASSWORD" \
#     --memory=512MB \
#     --timeout=540s \
#     --no-allow-unauthenticated

# resource "google_cloudfunctions2_function" "trigger" { ... }
