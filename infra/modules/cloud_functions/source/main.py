import os
from google.cloud import dataproc_v1


def trigger_dataproc_job(event, context):
    """
    Trigger de Cloud Functions gen1.
    Se dispara cuando un archivo nuevo llega al bucket GCS y lanza el ETL en Dataproc.
    """
    bucket = event["bucket"]
    name   = event["name"]

    # Filtrar: solo procesar archivos en raw/
    if not name.startswith("raw/"):
        print(f"Archivo ignorado (no está en raw/): {name}")
        return

    project = os.environ["GCP_PROJECT"]
    region  = os.environ["DATAPROC_REGION"]
    cluster = os.environ["DATAPROC_CLUSTER"]
    gcs_bucket = os.environ["GCS_BUCKET"]

    print(f"Nuevo archivo detectado: gs://{bucket}/{name}")
    print(f"Lanzando job Spark en cluster {cluster}...")

    job_client = dataproc_v1.JobControllerClient(
        client_options={"api_endpoint": f"{region}-dataproc.googleapis.com:443"}
    )

    job = {
        "placement": {"cluster_name": cluster},
        "pyspark_job": {
            "main_python_file_uri": f"gs://{gcs_bucket}/spark-jobs/etl_main.py",
            "args": [
                "--input",  f"gs://{bucket}/{name}",
                "--output", f"gs://{gcs_bucket}/processed/",
            ],
        },
    }

    operation = job_client.submit_job_as_operation(
        request={"project_id": project, "region": region, "job": job}
    )
    response = operation.result()
    print(f"Job completado: {response.reference.job_id}")
