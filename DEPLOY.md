# Guía de Despliegue — Supermarket Analytics

> **TL;DR rápido (desarrollo local):**
> ```powershell
> python -m venv .venv && .venv\Scripts\Activate.ps1
> pip install -r requirements.txt
> cd frontend && npm install && cd ..
> .\start.ps1
> ```
> API → http://localhost:8000/docs · Dashboard → http://localhost:3000

---

## Contenido

1. [Arquitectura](#1-arquitectura)
2. [Ejecución local](#2-ejecución-local)
3. [Despliegue en GCP — Cloud Run (demo rápido)](#3-despliegue-en-gcp--cloud-run-demo-rápido)
4. [CI/CD con Cloud Build (automático)](#4-cicd-con-cloud-build-automático)
5. [Arquitectura completa (Dataproc + Cloud Functions)](#5-arquitectura-completa-dataproc--cloud-functions)
6. [Variables de entorno de referencia](#6-variables-de-entorno-de-referencia)
7. [Endpoints del API](#7-endpoints-del-api)

---

## 1. Arquitectura

```
GitHub ──push──▶ Cloud Build ──build/push──▶ Artifact Registry
                                                   │
                        ┌──────────────────────────┤
                        ▼                          ▼
              Cloud Run (FastAPI)       Cloud Run (Next.js)
                   :8080                     :3000
                     │                          │
                     └──── PostgreSQL ◀─────────┘
                           (Cloud SQL)
                               ▲
                     Dataproc (Spark)
                               ▲
                     Cloud Storage (CSV /raw)
                               ▲
                     Cloud Functions (trigger)
```

**Modo demo (§3):** API y Frontend en Cloud Run leyendo CSV embebidos en la imagen.  
**Modo completo (§5):** Pipeline Dataproc procesa CSV, escribe en Cloud SQL, API consulta la BD.

---

## 2. Ejecución local

### Requisitos previos
| Herramienta | Versión mínima | Verificar |
|-------------|---------------|-----------|
| Python      | 3.10          | `python --version` |
| Node.js     | 18            | `node --version` |
| npm         | 9             | `npm --version` |

### Pasos

```powershell
# 1. Clonar / abrir el proyecto
cd Product-Recomendation-System

# 2. Entorno virtual Python (solo la primera vez)
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows
# source .venv/bin/activate          # macOS / Linux
pip install -r requirements.txt

# 3. Dependencias del frontend (solo la primera vez)
cd frontend
npm install
cd ..

# 4. Lanzar todo con el script automático
.\start.ps1
```

O manualmente en dos terminales separadas:

```powershell
# Terminal 1 — Backend
.venv\Scripts\Activate.ps1
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

**URLs:**
- Dashboard: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs
- API health: http://localhost:8000/api/health

---

## 3. Despliegue en GCP — Cloud Run (demo rápido)

Este modo empaqueta el dataset CSV dentro de la imagen Docker y despliega ambos servicios en Cloud Run. **No requiere Dataproc ni Cloud SQL.**

### 3.1 Prerrequisitos GCP

```bash
# Instalar Google Cloud SDK si no está instalado:
# https://cloud.google.com/sdk/docs/install

# Autenticarse
gcloud auth login
gcloud auth configure-docker us-central1-docker.pkg.dev

# Crear/seleccionar proyecto
gcloud config set project TU_PROJECT_ID
```

### 3.2 Habilitar APIs necesarias

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

### 3.3 Crear repositorio en Artifact Registry

```bash
gcloud artifacts repositories create supermarket-analytics \
  --repository-format=docker \
  --location=us-central1 \
  --description="Supermarket Analytics images"
```

### 3.4 Construir y desplegar el backend

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1
REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/supermarket-analytics"

# Build (desde la raíz del proyecto)
docker build \
  -t ${REPO}/supermarket-api:latest \
  -f api/Dockerfile \
  .

# Push
docker push ${REPO}/supermarket-api:latest

# Deploy a Cloud Run
gcloud run deploy supermarket-api \
  --image  ${REPO}/supermarket-api:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --port   8080
```

Anota la URL que devuelve el comando (forma: `https://supermarket-api-XXXXX-uc.a.run.app`).

### 3.5 Construir y desplegar el frontend

```bash
# Reemplaza la URL con la obtenida en el paso anterior
API_URL="https://supermarket-api-XXXXX-uc.a.run.app"

docker build \
  --build-arg NEXT_PUBLIC_API_URL=${API_URL} \
  -t ${REPO}/supermarket-frontend:latest \
  -f frontend/Dockerfile \
  frontend/

docker push ${REPO}/supermarket-frontend:latest

gcloud run deploy supermarket-frontend \
  --image  ${REPO}/supermarket-frontend:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --port   3000
```

La URL del frontend es la dirección pública del dashboard.

---

## 4. CI/CD con Cloud Build (automático)

Cada `git push` a `main` construye y despliega ambos servicios automáticamente.

### 4.1 Conectar repositorio GitHub a Cloud Build

1. Ir a **Cloud Build → Triggers → Connect repository** en la consola GCP.
2. Seleccionar GitHub y autorizar.
3. Elegir el repositorio del proyecto.

### 4.2 Crear trigger

```bash
# Primero obtén la URL del API (después del primer deploy manual en §3)
API_URL="https://supermarket-api-XXXXX-uc.a.run.app"

gcloud builds triggers create github \
  --name="supermarket-push-main" \
  --repo-name="Product-Recomendation-System" \
  --repo-owner="TU_GITHUB_USER" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --substitutions="_REGION=us-central1,_REPO=supermarket-analytics,_API_SERVICE=supermarket-api,_FRONT_SERVICE=supermarket-frontend,_API_URL=${API_URL}"
```

### 4.3 Dar permisos a la cuenta de servicio de Cloud Build

```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/artifactregistry.writer"
```

### 4.4 Trigger manual (opcional)

```bash
gcloud builds submit . \
  --config cloudbuild.yaml \
  --substitutions "_API_URL=https://supermarket-api-XXXXX-uc.a.run.app"
```

---

## 5. Arquitectura completa (Dataproc + Cloud Functions)

> Esta sección describe la arquitectura del diagrama GCP. Implementarla es opcional para la entrega — el modo Cloud Run (§3) es suficiente para la demo.

### Flujo de datos

```
CSV nuevo en GCS /raw
   → Cloud Functions detecta el evento
      → lanza job Dataproc (ETL → K-Means → Agregaciones)
         → resultados escritos en Cloud SQL (PostgreSQL)
            → FastAPI consulta Cloud SQL
```

### 5.1 Crear Cloud SQL (PostgreSQL)

```bash
gcloud sql instances create supermarket-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

gcloud sql databases create analytics --instance=supermarket-db
gcloud sql users set-password postgres --instance=supermarket-db --password=CHANGE_ME
```

### 5.2 Crear bucket GCS

```bash
PROJECT_ID=$(gcloud config get-value project)

gsutil mb -l us-central1 gs://${PROJECT_ID}-supermarket-data
gsutil cp -r DataSet/ gs://${PROJECT_ID}-supermarket-data/raw/
```

### 5.3 Crear cluster Dataproc

```bash
gcloud dataproc clusters create supermarket-cluster \
  --region=us-central1 \
  --num-workers=2 \
  --master-machine-type=n1-standard-2 \
  --worker-machine-type=n1-standard-2 \
  --image-version=2.1-debian11
```

### 5.4 Cloud Function — trigger de nuevos datos

```bash
# Subir el código de la función
gcloud functions deploy supermarket-trigger \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=scripts/cloud_function/ \
  --entry-point=on_new_file \
  --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
  --trigger-event-filters="bucket=${PROJECT_ID}-supermarket-data" \
  --set-env-vars "GCP_PROJECT=${PROJECT_ID},DATAPROC_CLUSTER=supermarket-cluster,GCP_REGION=us-central1"
```

### 5.5 Ejecutar jobs Spark manualmente (para prueba)

```bash
# Subir los scripts Spark
gsutil cp scripts/spark/*.py gs://${PROJECT_ID}-supermarket-data/scripts/

# ETL
gcloud dataproc jobs submit pyspark \
  gs://${PROJECT_ID}-supermarket-data/scripts/etl_job.py \
  --cluster=supermarket-cluster \
  --region=us-central1 \
  -- --bucket=${PROJECT_ID}-supermarket-data --project=${PROJECT_ID}

# Analytics (K-Means + Agregaciones)
gcloud dataproc jobs submit pyspark \
  gs://${PROJECT_ID}-supermarket-data/scripts/analytics_job.py \
  --cluster=supermarket-cluster \
  --region=us-central1 \
  -- --bucket=${PROJECT_ID}-supermarket-data --project=${PROJECT_ID}
```

---

## 6. Variables de entorno de referencia

| Variable | Uso | Ejemplo |
|----------|-----|---------|
| `DATA_DIR` | Ruta al dataset (backend) | `./DataSet/DataSet` |
| `NEXT_PUBLIC_API_URL` | URL del backend (frontend, build-time) | `https://supermarket-api-xxx.run.app` |
| `GCP_PROJECT_ID` | ID del proyecto GCP | `mi-proyecto-123` |
| `GCP_REGION` | Región de despliegue | `us-central1` |
| `GCS_BUCKET` | Nombre del bucket | `mi-proyecto-supermarket-data` |
| `DB_HOST` | Host Cloud SQL (modo completo) | `127.0.0.1` (via proxy) |
| `DB_NAME` | Nombre de la BD | `analytics` |
| `DB_USER` / `DB_PASSWORD` | Credenciales PostgreSQL | — |

Copiar `.env.example` a `.env` para desarrollo local.

---

## 7. Endpoints del API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/health` | Estado del servicio y conteos |
| GET | `/api/resumen` | KPIs, top productos/clientes, días pico, categorías |
| GET | `/api/visualizaciones` | Serie de tiempo, boxplot, heatmap de correlación |
| GET | `/api/patrones` | Actividad por día de semana, por tienda, frecuencia de compra |
| GET | `/api/segmentacion` | Clusters K-Means: puntos PCA + perfiles por segmento |
| GET | `/api/recomendacion?product_id=X` | Productos con mayor co-ocurrencia junto a X |
| GET | `/api/recomendacion?customer_id=Y` | Productos recomendados para el cliente Y |
| POST | `/api/reload` | **Recarga datos y recomputa todos los caches** (nuevo dataset) |

Documentación interactiva (Swagger UI): `<API_URL>/docs`

---

## 8. Incorporación de nuevos datos

### Modo demo (local / Cloud Run)

El endpoint `POST /api/reload` recarga los CSV desde `DATA_DIR` y recomputa todos los módulos:

```bash
# Local
curl -X POST http://localhost:8000/api/reload

# Cloud Run
curl -X POST https://<api-url>/api/reload
```

**Flujo para añadir datos nuevos (modo demo):**
1. Agrega o reemplaza archivos CSV en `DataSet/DataSet/Transactions/`.
2. Llama `POST /api/reload`.
3. El dashboard se actualiza automáticamente al recargar la página.

### Modo completo (Dataproc + Cloud Functions)

```
Nuevo CSV en GCS /raw
  → Cloud Function detecta `google.cloud.storage.object.v1.finalized`
    → Lanza jobs Spark: ETL → K-Means → Co-ocurrencia → Agregaciones
      → Resultados escritos en Cloud SQL
        → `POST /api/reload` (o reinicio del servicio) lee la BD actualizada
```

---

## Troubleshooting

**`docker: command not found`**  
Instalar Docker Desktop: https://docs.docker.com/desktop/

**Error 403 al hacer push a Artifact Registry**  
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

**Frontend muestra "API desconectado"**  
Verificar que `NEXT_PUBLIC_API_URL` apunte a la URL correcta del backend (sin `/` al final) y que el servicio Cloud Run esté corriendo:
```bash
gcloud run services describe supermarket-api --region us-central1
```

**Cloud Run timeout al arrancar**  
El backend tarda ~5 s en cargar y procesar los CSV. Aumentar el timeout de arranque:
```bash
gcloud run services update supermarket-api --region us-central1 --timeout 120
```

**`standalone` output falla en Next.js**  
Verificar que `next.config.mjs` tenga `output: "standalone"` y que la versión de Next.js sea ≥ 13.
