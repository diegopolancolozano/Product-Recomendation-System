"""
Cloud Function Gen2 — Trigger de nuevos datos.
Corresponde al contenedor "Cloud Functions" del diagrama GCP.

Flujo:
  1. Nuevo CSV llega a gs://<bucket>/raw/Transactions/
  2. Esta funcion se activa (GCS trigger)
  3. Envia los tres jobs Spark a Dataproc SIN ESPERAR (async)
     — El limite de 540s no permite esperar la ejecucion completa
     — Dataproc ejecuta los jobs de forma independiente en el cluster
"""
import os
import time
import functions_framework
from googleapiclient import discovery


def _submit_job(dataproc, project: str, region: str, cluster: str,
                script_uri: str, args: list[str], job_id: str) -> str:
    """Envia un PySpark job a Dataproc y retorna el job_id."""
    job_body = {
        "placement": {"clusterName": cluster},
        "reference": {"jobId": job_id},
        "pySparkJob": {
            "mainPythonFileUri": script_uri,
            "args": args,
            "jarFileUris": [
                "gs://spark-lib/postgresql/postgresql-42.6.0.jar",
            ],
        },
    }
    result = (
        dataproc.projects()
        .regions()
        .jobs()
        .submit(projectId=project, region=region, body={"job": job_body})
        .execute()
    )
    submitted_id = result["reference"]["jobId"]
    print(f"Job enviado: {submitted_id}")
    return submitted_id


@functions_framework.cloud_event
def main(cloud_event: functions_framework.CloudEvent) -> None:
    data   = cloud_event.data
    bucket = data.get("bucket", "")
    name   = data.get("name", "")

    print(f"Archivo detectado: gs://{bucket}/{name}")

    if not name.startswith("raw/Transactions/") or not name.endswith(".csv"):
        print(f"Ignorado: {name}")
        return

    project  = os.environ["GCP_PROJECT"]
    region   = os.environ.get("REGION", "us-central1")
    cluster  = os.environ.get("DATAPROC_CLUSTER", "supermarket-spark")
    db_host  = os.environ["DB_HOST"]
    db_pass  = os.environ["DB_PASSWORD"]
    gcs_jobs = f"gs://{bucket}/spark"

    common_args = [
        f"--db_host={db_host}",
        "--db_user=supermarket",
        f"--db_password={db_pass}",
    ]

    dataproc = discovery.build("dataproc", "v1")
    ts       = str(int(time.time()))

    # Enviar los tres jobs. Dataproc los ejecuta en el cluster.
    # Los jobs se encolan automaticamente si el cluster esta ocupado.
    etl_id = _submit_job(
        dataproc, project, region, cluster,
        script_uri=f"{gcs_jobs}/01_etl.py",
        args=[f"--bucket={bucket}"] + common_args,
        job_id=f"etl-{ts}",
    )

    ml_id = _submit_job(
        dataproc, project, region, cluster,
        script_uri=f"{gcs_jobs}/02_ml.py",
        args=common_args,
        job_id=f"ml-{ts}",
    )

    agg_id = _submit_job(
        dataproc, project, region, cluster,
        script_uri=f"{gcs_jobs}/03_aggregations.py",
        args=common_args,
        job_id=f"agg-{ts}",
    )

    print(f"Pipeline iniciado — jobs enviados: {etl_id}, {ml_id}, {agg_id}")
    print("Los jobs corren de forma independiente en Dataproc.")
