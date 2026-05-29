"""
FastAPI backend — Supermarket Analytics API.
Corresponde al contenedor "Cloud Run — FastAPI" del diagrama de arquitectura GCP.

Endpoints:
  GET /api/health           → estado del servicio
  GET /api/resumen          → KPIs del Resumen Ejecutivo
  GET /api/visualizaciones  → datos para las Visualizaciones Analíticas
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Asegurar que el directorio raíz del proyecto está en el path de Python
# ---------------------------------------------------------------------------
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.analytics import compute_kpis, build_product_labels, compute_patterns
from src.data_loader import load_data

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
DATA_DIR = Path(
    os.getenv("DATA_DIR", str(ROOT / "DataSet" / "DataSet"))
)

app = FastAPI(
    title="Supermarket Analytics API",
    description="API REST para el análisis de transacciones de supermercado.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Caché en memoria — se llena una vez al arrancar el servidor
_cache: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Startup: carga y pre-cómputo
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup_event() -> None:
    global _cache
    try:
        data = load_data(DATA_DIR)
        transactions: pd.DataFrame = data["transactions"]
        items: pd.DataFrame = data["items"]
        kpis = compute_kpis(transactions, items)
        patterns = compute_patterns(transactions, items)
        _cache["data"] = data
        _cache["kpis"] = kpis
        _cache["patterns"] = patterns
        print(
            f"Datos cargados — "
            f"{kpis['total_transactions']} transacciones, "
            f"{kpis['total_units']} unidades"
        )
    except Exception as exc:
        print(f"Error al cargar datos: {exc}")


# ---------------------------------------------------------------------------
# Utilidades de serialización
# ---------------------------------------------------------------------------
def _safe_float(val: Any) -> float | None:
    """Devuelve None si el valor no es JSON-serializable."""
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _boxplot_stats(series: pd.Series) -> dict:
    """Calcula estadísticas de un boxplot estándar (Tukey)."""
    q1 = float(series.quantile(0.25))
    median = float(series.quantile(0.50))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    whisker_low = float(max(series.min(), q1 - 1.5 * iqr))
    whisker_high = float(min(series.max(), q3 + 1.5 * iqr))
    outliers_vals = series[
        (series < whisker_low) | (series > whisker_high)
    ].tolist()
    return {
        "whisker_low": whisker_low,
        "q1": q1,
        "median": median,
        "q3": q3,
        "whisker_high": whisker_high,
        "mean": float(series.mean()),
        "std": float(series.std()),
        "total_customers": int(len(series)),
        "outlier_count": len(outliers_vals),
        "outliers": [float(o) for o in outliers_vals[:200]],
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "data_loaded": bool(_cache),
        "transactions": _cache.get("kpis", {}).get("total_transactions", 0),
        "units": _cache.get("kpis", {}).get("total_units", 0),
    }


@app.get("/api/resumen")
def get_resumen() -> dict:
    """Resumen Ejecutivo: KPIs, top productos/clientes, días pico, categorías."""
    if "kpis" not in _cache:
        raise HTTPException(status_code=503, detail="Datos aún no disponibles.")

    kpis = _cache["kpis"]

    top_products = [
        {
            "product_id": int(row["product_id"]),
            "label": str(row["label"]),
            "units": int(row["units"]),
        }
        for _, row in kpis["top_products"].iterrows()
    ]

    top_customers = [
        {
            "customer_id": str(row["customer_id"]),
            "label": str(row["customer_label"]),
            "transactions": int(row["transactions"]),
        }
        for _, row in kpis["top_customers"].iterrows()
    ]

    transactions_per_day = [
        {
            "date": str(row["date"]),
            "transactions": int(row["transactions"]),
        }
        for _, row in kpis["transactions_per_day"].iterrows()
    ]

    category_units = [
        {
            "category_name": str(row["category_name"]),
            "units": int(row["units"]),
        }
        for _, row in kpis["category_units"].iterrows()
    ]

    return {
        "total_units": int(kpis["total_units"]),
        "total_transactions": int(kpis["total_transactions"]),
        "top_products": top_products,
        "top_customers": top_customers,
        "transactions_per_day": transactions_per_day,
        "category_units": category_units,
    }


@app.get("/api/visualizaciones")
def get_visualizaciones() -> dict:
    """Visualizaciones Analíticas: serie de tiempo, boxplot, heatmap de correlación."""
    if "kpis" not in _cache:
        raise HTTPException(status_code=503, detail="Datos aún no disponibles.")

    kpis = _cache["kpis"]

    # Serie de tiempo: unidades vendidas por día
    units_per_day = [
        {
            "date": str(row["date"]),
            "units": int(row["units"]),
        }
        for _, row in kpis["units_per_day"].iterrows()
    ]

    # Boxplot: distribución de unidades totales por cliente
    customer_units_series = kpis["customer_units"]["total_units"]
    boxplot = _boxplot_stats(customer_units_series)

    # Heatmap de correlación
    corr_df: pd.DataFrame = kpis["customer_corr"]
    correlation_matrix: list[dict] = []
    corr_labels: list[str] = []

    if not corr_df.empty:
        corr_labels = [str(c) for c in corr_df.columns.tolist()]
        for row_name in corr_df.index:
            for col_name in corr_df.columns:
                raw = corr_df.loc[row_name, col_name]
                val = _safe_float(raw)
                if val is None:
                    val = 0.0
                correlation_matrix.append({
                    "x": str(col_name),
                    "y": str(row_name),
                    "value": round(val, 3),
                })

    return {
        "units_per_day": units_per_day,
        "boxplot": boxplot,
        "correlation_matrix": correlation_matrix,
        "correlation_labels": corr_labels,
    }


@app.get("/api/patrones")
def get_patrones() -> dict:
    """Patrones temporales y espaciales: día de semana, tienda, frecuencia de compra."""
    if "patterns" not in _cache:
        raise HTTPException(status_code=503, detail="Datos aún no disponibles.")
    return _cache["patterns"]
