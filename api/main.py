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

from src.analytics import (
    compute_kpis,
    build_product_labels,
    compute_patterns,
    run_kmeans,
    build_cooccurrence,
    recommend_for_product,
    recommend_for_customer,
    build_customer_features,
)
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
        # Segmentación K-Means (k=4 o menos si pocos clientes)
        customer_features = build_customer_features(transactions, items)
        clustered: pd.DataFrame = pd.DataFrame()
        summary: pd.DataFrame = pd.DataFrame()
        n_clusters = 0
        if len(customer_features) >= 4:
            n_clusters = min(4, len(customer_features))
            clustered, summary = run_kmeans(customer_features, k=n_clusters)

        # Co-ocurrencia para recomendaciones
        item_counts, pair_counts = build_cooccurrence(items, min_item_support=5)
        product_labels = build_product_labels(items)

        _cache["data"] = data
        _cache["kpis"] = kpis
        _cache["patterns"] = patterns
        _cache["segmentation"] = {
            "clustered": clustered,
            "summary": summary,
            "n_clusters": n_clusters,
        }
        _cache["cooccurrence"] = {
            "item_counts": item_counts,
            "pair_counts": pair_counts,
        }
        _cache["product_labels"] = product_labels

        print(
            f"Datos cargados — "
            f"{kpis['total_transactions']} transacciones, "
            f"{kpis['total_units']} unidades, "
            f"{len(customer_features)} clientes, "
            f"{len(item_counts)} productos en co-ocurrencia"
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


@app.get("/api/segmentacion")
def get_segmentacion() -> dict:
    """
    Segmentación K-Means de clientes.
    Devuelve coordenadas PCA por cliente (para scatter plot) y perfil promedio de cada cluster.
    """
    if "segmentation" not in _cache:
        raise HTTPException(status_code=503, detail="Datos aún no disponibles.")

    seg = _cache["segmentation"]
    clustered: pd.DataFrame = seg["clustered"]
    summary: pd.DataFrame = seg["summary"]
    n_clusters: int = seg["n_clusters"]

    if clustered.empty:
        return {"points": [], "profiles": [], "n_clusters": 0}

    # Cluster sizes
    cluster_sizes: dict = clustered["cluster"].value_counts().to_dict()

    # Serializar puntos (máx 3000 para rendimiento en frontend)
    sample = clustered if len(clustered) <= 3000 else clustered.sample(3000, random_state=42)
    points = [
        {
            "customer_id": str(row["customer_id"]),
            "cluster": int(row["cluster"]),
            "pca1": round(float(row["pca1"]), 4),
            "pca2": round(float(row["pca2"]), 4),
            "frequency": int(row["frequency"]),
            "total_units": int(row["total_units"]),
            "unique_products": int(row["unique_products"]),
            "unique_categories": int(row["unique_categories"]),
            "avg_basket_size": round(float(row["avg_basket_size"]), 2),
        }
        for _, row in sample.iterrows()
    ]

    # Perfiles por cluster
    profiles = [
        {
            "cluster": int(row["cluster"]),
            "frequency": round(float(row["frequency"]), 1),
            "total_units": round(float(row["total_units"]), 1),
            "unique_products": round(float(row["unique_products"]), 1),
            "unique_categories": round(float(row["unique_categories"]), 1),
            "avg_basket_size": round(float(row["avg_basket_size"]), 2),
            "size": int(cluster_sizes.get(int(row["cluster"]), 0)),
        }
        for _, row in summary.iterrows()
    ]

    return {"points": points, "profiles": profiles, "n_clusters": n_clusters}


@app.get("/api/recomendacion")
def get_recomendacion(
    product_id: int | None = None,
    customer_id: str | None = None,
    top_n: int = 10,
) -> dict:
    """
    Recomendación por co-ocurrencia.
    - ?product_id=X  → productos frecuentemente comprados junto a X
    - ?customer_id=Y → productos que Y aún no compró pero son compatibles con su historial
    """
    if "cooccurrence" not in _cache:
        raise HTTPException(status_code=503, detail="Datos aún no disponibles.")
    if product_id is None and customer_id is None:
        raise HTTPException(status_code=400, detail="Indica product_id o customer_id como query param.")

    item_counts = _cache["cooccurrence"]["item_counts"]
    pair_counts = _cache["cooccurrence"]["pair_counts"]
    labels: dict = _cache.get("product_labels", {})

    if product_id is not None:
        df = recommend_for_product(product_id, item_counts, pair_counts, top_n)
        if df.empty:
            return {"query": {"type": "product", "id": product_id}, "results": []}
        results = [
            {
                "product_id": int(row["product_id"]),
                "label": labels.get(int(row["product_id"]), f"Product {int(row['product_id'])}"),
                "support": int(row["support"]),
                "score": round(float(row["confidence"]), 4),
                "score_label": "Confianza",
            }
            for _, row in df.iterrows()
        ]
        return {"query": {"type": "product", "id": product_id}, "results": results}

    # Por cliente
    data = _cache.get("data")
    if data is None:
        raise HTTPException(status_code=503, detail="Datos aún no disponibles.")
    df = recommend_for_customer(
        str(customer_id), data["items"], item_counts, pair_counts, top_n
    )
    if df.empty:
        return {"query": {"type": "customer", "id": customer_id}, "results": []}
    results = [
        {
            "product_id": int(row["product_id"]),
            "label": labels.get(int(row["product_id"]), f"Product {int(row['product_id'])}"),
            "support": int(row["support"]),
            "score": round(float(row["score"]), 4),
            "score_label": "Score",
        }
        for _, row in df.iterrows()
    ]
    return {"query": {"type": "customer", "id": customer_id}, "results": results}


@app.post("/api/reload")
def reload_data() -> dict:
    """
    Recarga los datos desde DATA_DIR y recomputa todos los caches.
    Equivale al trigger de Cloud Functions cuando llegan nuevos datos.
    """
    global _cache
    try:
        data = load_data(DATA_DIR)
        transactions: pd.DataFrame = data["transactions"]
        items: pd.DataFrame = data["items"]

        kpis = compute_kpis(transactions, items)
        patterns = compute_patterns(transactions, items)

        customer_features = build_customer_features(transactions, items)
        clustered: pd.DataFrame = pd.DataFrame()
        summary: pd.DataFrame = pd.DataFrame()
        n_clusters = 0
        if len(customer_features) >= 4:
            n_clusters = min(4, len(customer_features))
            clustered, summary = run_kmeans(customer_features, k=n_clusters)

        item_counts, pair_counts = build_cooccurrence(items, min_item_support=5)
        product_labels = build_product_labels(items)

        _cache = {
            "data": data,
            "kpis": kpis,
            "patterns": patterns,
            "segmentation": {
                "clustered": clustered,
                "summary": summary,
                "n_clusters": n_clusters,
            },
            "cooccurrence": {
                "item_counts": item_counts,
                "pair_counts": pair_counts,
            },
            "product_labels": product_labels,
        }
        return {
            "status": "ok",
            "transactions": int(kpis["total_transactions"]),
            "units": int(kpis["total_units"]),
            "customers": int(len(customer_features)),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
