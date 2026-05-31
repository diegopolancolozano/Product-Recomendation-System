# Product Recommendation System — Supermarket Analytics

**Proyecto final · Procesamiento Distribuido de Datos**  

**Integrantes:**

- Ricardo Andrés Chamorro Martínez

- Diego Armando Polanco Lozano

---

## Objetivo

Solución funcional para análisis descriptivo y diagnóstico de transacciones de supermercado, con segmentación y recomendación de productos.

---

## Arquitectura (GCP)

![Arquitectura General del Proyecto](Arquitectura%20General%20Proyecto.png)

Ver [diagrama_nube.md](diagrama_nube.md) para el modelo C4 completo.

---

## Estructura del proyecto

```
.
├── api/
│   └── main.py          # FastAPI — endpoints /resumen, /visualizaciones, /segmentacion, /recomendacion
├── src/
│   ├── data_loader.py   # Carga y normalización de CSV
│   └── analytics.py     # KPIs, K-Means, co-ocurrencia, recomendador
├── frontend/
│   └── src/
│       ├── app/         # Next.js App Router (page.tsx, layout.tsx)
│       ├── components/  # KPICards, HorizontalBarChart, SimpleLineChart, BoxPlot, CorrelationHeatmap…
│       └── types/       # Tipos TypeScript para las respuestas del API
├── DataSet/DataSet/
│   ├── Products/
│   │   ├── Categories.csv
│   │   └── ProductCategory.csv
│   └── Transactions/
│       └── *_Tran.csv
├── requirements.txt
├── start.ps1            # Script de inicio rápido (Windows)
└── README.md
```

---

## Despliegue

Ver **[DEPLOY.md](DEPLOY.md)** para instrucciones completas:
- Ejecución local (Windows / macOS / Linux)
- Despliegue en GCP Cloud Run (demo rápido, sin Dataproc)
- CI/CD con Cloud Build (automático en push a `main`)
- Arquitectura completa (Dataproc + Cloud Functions + Cloud SQL)

---

## Ejecución local (desarrollo)

### Prerequisitos
- Python ≥ 3.10
- Node.js ≥ 18

### Opción A — Script automático (recomendado)

```powershell
# 1. Crear entorno virtual (solo la primera vez)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Instalar dependencias del frontend (solo la primera vez)
cd frontend
npm install
cd ..

# 3. Lanzar todo con un solo comando
.\start.ps1
```

Abre automáticamente dos ventanas:
- **Backend API:** http://localhost:8000 · Docs: http://localhost:8000/docs  
- **Frontend:** http://localhost:3000

---

### Opción B — Manual (dos terminales)

**Terminal 1 — FastAPI backend:**
```powershell
.venv\Scripts\Activate.ps1
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — Next.js frontend:**
```powershell
cd frontend
npm run dev
```

---

## Endpoints del API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/health` | Estado del servicio y conteos |
| GET | `/api/resumen` | KPIs, top productos/clientes, días pico, categorías |
| GET | `/api/visualizaciones` | Serie de tiempo, boxplot, heatmap de correlación |
| GET | `/api/patrones` | Actividad por día de semana, por tienda, frecuencia de compra |
| GET | `/api/segmentacion` | Clusters K-Means (k=4): coordenadas PCA + perfil de cada segmento |
| GET | `/api/recomendacion` | Co-ocurrencia: `?product_id=X` o `?customer_id=Y` |
| POST | `/api/reload` | Recarga datos desde `DATA_DIR` y recomputa todos los caches |

Swagger UI disponible en: http://localhost:8000/docs

---

## Módulos implementados

### Resumen Ejecutivo
- Total unidades vendidas · Número de transacciones · Canasta promedio · Clientes únicos (KPIs)
- Top 10 productos por volumen (barras horizontales)
- Top 10 clientes por compras (barras horizontales)
- Días pico de compra (serie de tiempo)
- Categorías más relevantes (pastel)

### Visualizaciones Analíticas
- Ventas diarias — serie de tiempo con promedio de referencia
- Distribución de unidades por cliente — boxplot (Tukey) con estadísticas
- Correlación entre variables del cliente — heatmap de Pearson

### Patrones de Compra *(nuevo)*
- Actividad promedio por día de la semana (bar chart con intensidad semafórica)
- Frecuencia de compra por cliente — histograma de recurrencia
- Actividad por tienda (si hay múltiples `store_id` en el dataset)

### Segmentación de Clientes
- K-Means (k=4) sobre 5 variables: frecuencia, volumen, productos únicos, categorías, canasta promedio
- Visualización scatter con proyección PCA (2 componentes)
- Perfil automático de cada segmento con descripción interpretativa

### Recomendador de Productos
- Filtrado colaborativo por co-ocurrencia (soporte mínimo = 5 transacciones)
- Búsqueda por producto: qué se compra junto a X (confianza P(B|A))
- Búsqueda por cliente: qué debería comprar según historial (score acumulado)

### Incorporación de nuevos datos
- `POST /api/reload` recomputa todos los módulos al recibir datos frescos
- En arquitectura Dataproc: Cloud Functions detecta CSV nuevo en GCS y lanza los jobs Spark

---

## Datos

| Archivo | Formato | Descripción |
|---------|---------|-------------|
| `Transactions/*_Tran.csv` | `fecha\|tienda\|cliente\|lista_productos` | Transacciones por tienda |
| `Products/ProductCategory.csv` | `product_id\|category_id` | Mapeo producto → categoría |
| `Products/Categories.csv` | `category_id\|category_name` | Nombres de categorías |

**Nota:** No hay precios. Las métricas se basan en volumen y frecuencia.
