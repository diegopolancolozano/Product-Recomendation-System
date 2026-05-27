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
| GET | `/api/health` | Estado del servicio |
| GET | `/api/resumen` | KPIs, top productos/clientes, días pico, categorías |
| GET | `/api/visualizaciones` | Serie de tiempo, boxplot, heatmap de correlación |

Swagger UI disponible en: http://localhost:8000/docs

---

## Módulos implementados

### Resumen Ejecutivo
- Total unidades vendidas (KPI)
- Número de transacciones (KPI)
- Top 10 productos por volumen (barras horizontales)
- Top 10 clientes por compras (barras horizontales)
- Días pico de compra (serie de tiempo)
- Categorías más relevantes (barras horizontales)

### Visualizaciones Analíticas
- Ventas diarias — serie de tiempo con promedio de referencia
- Distribución de unidades por cliente — boxplot (Tukey) con estadísticas
- Correlación entre variables del cliente — heatmap de Pearson

### Análisis Avanzado (próxima entrega)
- Segmentación K-Means (`/api/segmentacion`)
- Recomendador por co-ocurrencia (`/api/recomendacion`)
- Incorporación de nuevos datos en tiempo real

---

## Datos

| Archivo | Formato | Descripción |
|---------|---------|-------------|
| `Transactions/*_Tran.csv` | `fecha\|tienda\|cliente\|lista_productos` | Transacciones por tienda |
| `Products/ProductCategory.csv` | `product_id\|category_id` | Mapeo producto → categoría |
| `Products/Categories.csv` | `category_id\|category_name` | Nombres de categorías |

**Nota:** No hay precios. Las métricas se basan en volumen y frecuencia.
