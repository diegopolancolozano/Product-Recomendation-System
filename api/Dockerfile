# ── Supermarket Analytics — FastAPI backend ───────────────────────────────────
# Imagen ligera de producción para Cloud Run.
# El dataset CSV se copia dentro de la imagen para el despliegue demo.
# Para producción completa (GCP), reemplazar con lectura desde Cloud Storage.

FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema (solo las necesarias para compilar paquetes nativos)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python primero (capa cacheada)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la aplicación
COPY api/   ./api/
COPY src/   ./src/
# Dataset incluido en la imagen para el modo demo
# Para producción real, montar desde GCS y setear DATA_DIR
COPY DataSet/ ./DataSet/

# Cloud Run inyecta PORT en tiempo de ejecución (por defecto 8080)
EXPOSE 8080
ENV PORT=8080

CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT}
