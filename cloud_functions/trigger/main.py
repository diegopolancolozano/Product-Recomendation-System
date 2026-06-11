"""
Cloud Function Gen2 — Trigger de nuevos datos.
Corresponde al contenedor "Cloud Functions" del diagrama GCP.

Flujo:
  1. Nuevo CSV llega a gs://<bucket>/raw/Transactions/
  2. Esta funcion se activa (GCS trigger)
  3. Ejecuta ETL primero y espera que termine (max 300s)
  4. Solo si ETL termina OK, lanza AGG y ML (async)
     — AGG y ML necesitan que staging.transactions exista
"""
import json
import os
import time
import urllib.request
import functions_framework
from googleapiclient import discovery


def _submit_job(dataproc, project: str, region: str, cluster: str,
                script_uri: str, args: list[str], job_id: str,
                jar_uris: list[str] | None = None) -> str:
    """Envia un PySpark job a Dataproc y retorna el job_id."""
    job_body = {
        "placement": {"clusterName": cluster},
        "reference": {"jobId": job_id},
        "pysparkJob": {
            "mainPythonFileUri": script_uri,
            "args": args,
            "jarFileUris": jar_uris or [],
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


def _wait_for_job(dataproc, project: str, region: str, job_id: str,
                  timeout: int = 300) -> str:
    """Espera a que un job termine. Retorna el estado final (DONE/ERROR/CANCELLED)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = (
            dataproc.projects()
            .regions()
            .jobs()
            .get(projectId=project, region=region, jobId=job_id)
            .execute()
        )
        state = result["status"]["state"]
        if state in ("DONE", "ERROR", "CANCELLED"):
            print(f"Job {job_id} finalizo con estado: {state}")
            return state
        time.sleep(10)
    print(f"Timeout esperando job {job_id} despues de {timeout}s")
    return "TIMEOUT"


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
    pg_jar   = [f"gs://{bucket}/spark/postgresql-42.6.0.jar"]

    # Siempre recargar el API desde GCS para reflejar el nuevo archivo,
    # incluso si Dataproc falla (cluster apagado, stockout, etc.)
    try:
        # ── Paso 1: ETL — esperar que termine antes de AGG/ML ────────────────
        etl_id = _submit_job(
            dataproc, project, region, cluster,
            script_uri=f"{gcs_jobs}/01_etl.py",
            args=[f"--bucket={bucket}"] + common_args,
            job_id=f"etl-{ts}",
            jar_uris=pg_jar,
        )

        etl_state = _wait_for_job(dataproc, project, region, etl_id, timeout=300)

        if etl_state != "DONE":
            print(f"ETL termino con error ({etl_state}). No se ejecutan AGG ni ML.")
        else:
            # ── Paso 2: AGG y ML — solo si ETL fue exitoso ───────────────────
            print("ETL completado. Lanzando AGG y ML...")

            agg_id = _submit_job(
                dataproc, project, region, cluster,
                script_uri=f"{gcs_jobs}/03_aggregations.py",
                args=common_args,
                job_id=f"agg-{ts}",
                jar_uris=pg_jar,
            )

            ml_id = _submit_job(
                dataproc, project, region, cluster,
                script_uri=f"{gcs_jobs}/02_ml.py",
                args=common_args,
                job_id=f"ml-{ts}",
                jar_uris=pg_jar,
            )

            print(f"Pipeline iniciado — ETL: {etl_id} (DONE), AGG: {agg_id}, ML: {ml_id}")
            print("AGG y ML corren de forma independiente en Dataproc.")

    except Exception as exc:
        print(f"Dataproc no disponible ({exc}). Procediendo con reload del API desde GCS.")

    # Notificar al API para que descargue el CSV nuevo desde GCS
    # (se ejecuta siempre, con o sin Dataproc)
    _trigger_api_reload()


def _trigger_api_reload() -> None:
    """Llama al endpoint /api/reload del backend para que descargue los CSVs nuevos de GCS."""
    api_url = os.environ.get("API_URL", "")
    if not api_url:
        print("API_URL no configurado, omitiendo reload del API.")
        return
    try:
        req = urllib.request.Request(
            f"{api_url}/api/reload",
            data=json.dumps({}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"API reload disparado: HTTP {resp.status}")
    except Exception as exc:
        print(f"API reload fallido (no critico): {exc}")
