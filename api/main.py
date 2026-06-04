"""FastAPI backend — Supermarket Analytics API."""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.analytics import (
    build_customer_features,
    build_product_labels,
    build_cooccurrence,
    compute_kpis,
    compute_patterns,
    recommend_for_customer,
    recommend_for_product,
    run_kmeans,
)
from src.data_loader import load_data

DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT / "DataSet" / "DataSet")))

app = FastAPI(title="Supermarket Analytics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache: dict[str, Any] = {}


def _build_cache(data: dict) -> dict:
    """Computa todos los artefactos analiticos y retorna el cache completo."""
    transactions: pd.DataFrame = data["transactions"]
    items: pd.DataFrame        = data["items"]

    print("[1/5] KPIs y patrones...")
    kpis     = compute_kpis(transactions, items)
    patterns = compute_patterns(transactions, items)

    print("[2/5] Features y K-Means...")
    features = build_customer_features(transactions, items)
    clustered, summary = run_kmeans(features, k=4)
    cluster_sizes = clustered["cluster"].value_counts().to_dict() if not clustered.empty else {}

    print("[3/5] Co-ocurrencia de productos...")
    item_counts, pair_counts = build_cooccurrence(items, min_item_support=30)
    product_labels = build_product_labels(items)
    product_ids    = sorted(item_counts.keys())
    customer_ids   = sorted(transactions["customer_id"].dropna().unique().tolist())

    print(f"      {len(product_ids)} productos | {len(pair_counts):,} pares")
    return {
        "data":           data,
        "kpis":           kpis,
        "patterns":       patterns,
        "kmeans":         {"clustered": clustered, "summary": summary, "cluster_sizes": cluster_sizes},
        "cooccurrence":   (item_counts, pair_counts),
        "product_labels": product_labels,
        "product_ids":    product_ids,
        "customer_ids":   customer_ids[:2000],
    }


@app.on_event("startup")
def startup_event() -> None:
    global _cache
    try:
        print("[0/5] Cargando archivos CSV...")
        data = load_data(DATA_DIR)
        print(f"      {len(data['transactions']):,} transacciones | {len(data['items']):,} items")
        _cache = _build_cache(data)
        kpis = _cache["kpis"]
        print(
            f"Listo. {kpis['total_transactions']:,} transacciones | "
            f"{kpis['total_units']:,} unidades"
        )
    except Exception as exc:
        print(f"Error al cargar datos: {exc}")
        raise


def _safe_float(val: Any) -> float | None:
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _boxplot_stats(series: pd.Series) -> dict:
    q1  = float(series.quantile(0.25))
    med = float(series.quantile(0.50))
    q3  = float(series.quantile(0.75))
    iqr = q3 - q1
    wl  = float(max(series.min(), q1 - 1.5 * iqr))
    wh  = float(min(series.max(), q3 + 1.5 * iqr))
    out = series[(series < wl) | (series > wh)].tolist()
    return {
        "whisker_low": wl, "q1": q1, "median": med, "q3": q3, "whisker_high": wh,
        "mean": float(series.mean()), "std": float(series.std()),
        "total_customers": int(len(series)), "outlier_count": len(out),
        "outliers": [float(o) for o in out[:200]],
    }


# ── Endpoints ────────────────────────────────────────────────────────────────

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
    if "kpis" not in _cache:
        raise HTTPException(status_code=503, detail="Datos no disponibles.")
    kpis = _cache["kpis"]
    return {
        "total_units":        int(kpis["total_units"]),
        "total_transactions": int(kpis["total_transactions"]),
        "top_products": [
            {"product_id": int(r["product_id"]), "label": str(r["label"]), "units": int(r["units"])}
            for _, r in kpis["top_products"].iterrows()
        ],
        "top_customers": [
            {"customer_id": str(r["customer_id"]), "label": str(r["customer_label"]), "transactions": int(r["transactions"])}
            for _, r in kpis["top_customers"].iterrows()
        ],
        "transactions_per_day": [
            {"date": str(r["date"]), "transactions": int(r["transactions"])}
            for _, r in kpis["transactions_per_day"].iterrows()
        ],
        "category_units": [
            {"category_name": str(r["category_name"]), "units": int(r["units"])}
            for _, r in kpis["category_units"].iterrows()
        ],
    }


@app.get("/api/visualizaciones")
def get_visualizaciones() -> dict:
    if "kpis" not in _cache:
        raise HTTPException(status_code=503, detail="Datos no disponibles.")
    kpis = _cache["kpis"]
    units_per_day = [
        {"date": str(r["date"]), "units": int(r["units"])}
        for _, r in kpis["units_per_day"].iterrows()
    ]
    boxplot = _boxplot_stats(kpis["customer_units"]["total_units"])
    corr_df: pd.DataFrame = kpis["customer_corr"]
    correlation_matrix: list[dict] = []
    corr_labels: list[str] = []
    if not corr_df.empty:
        corr_labels = [str(c) for c in corr_df.columns.tolist()]
        for rn in corr_df.index:
            for cn in corr_df.columns:
                v = _safe_float(corr_df.loc[rn, cn]) or 0.0
                correlation_matrix.append({"x": str(cn), "y": str(rn), "value": round(v, 3)})
    return {
        "units_per_day":      units_per_day,
        "boxplot":            boxplot,
        "correlation_matrix": correlation_matrix,
        "correlation_labels": corr_labels,
    }


@app.get("/api/patrones")
def get_patrones() -> dict:
    if "patterns" not in _cache:
        raise HTTPException(status_code=503, detail="Datos no disponibles.")
    return _cache["patterns"]


@app.get("/api/avanzado")
def get_avanzado() -> dict:
    """Segmentacion K-Means + listas para el recomendador."""
    if "kmeans" not in _cache:
        raise HTTPException(status_code=503, detail="Datos de segmentacion no disponibles.")

    clustered: pd.DataFrame = _cache["kmeans"]["clustered"]
    summary:   pd.DataFrame = _cache["kmeans"]["summary"]
    cluster_sizes: dict      = _cache["kmeans"]["cluster_sizes"]
    labels = _cache.get("product_labels", {})

    sample = (
        clustered.sample(4000, random_state=42)
        if len(clustered) > 4000 else clustered
    )

    scatter = [
        {
            "customer_id":     str(r["customer_id"]),
            "pca1":            round(float(r["pca1"]), 4),
            "pca2":            round(float(r["pca2"]), 4),
            "cluster":         int(r["cluster"]),
            "frequency":       int(r["frequency"]),
            "total_units":     int(r["total_units"]),
            "unique_products": int(r["unique_products"]),
            "avg_basket_size": round(float(r["avg_basket_size"]), 1),
        }
        for _, r in sample.iterrows()
    ]

    cluster_summary = [
        {
            "cluster":           int(r["cluster"]),
            "frequency":         round(float(r["frequency"]), 2),
            "total_units":       round(float(r["total_units"]), 2),
            "unique_products":   round(float(r["unique_products"]), 2),
            "unique_categories": round(float(r["unique_categories"]), 2),
            "avg_basket_size":   round(float(r["avg_basket_size"]), 2),
            "size":              int(cluster_sizes.get(int(r["cluster"]), 0)),
        }
        for _, r in summary.iterrows()
    ]

    product_options = [
        {"product_id": pid, "label": labels.get(pid, f"Product {pid}")}
        for pid in _cache.get("product_ids", [])
    ]

    return {
        "scatter":         scatter,
        "cluster_summary": cluster_summary,
        "k":               len(cluster_summary),
        "product_options": product_options,
        "customer_ids":    _cache.get("customer_ids", [])[:500],
    }


@app.get("/api/recomendar/producto")
def recomendar_producto(
    product_id: int = Query(..., description="ID del producto base"),
    top_n:      int = Query(10, ge=1, le=20),
) -> dict:
    if "cooccurrence" not in _cache:
        raise HTTPException(status_code=503, detail="Datos no disponibles.")
    item_counts, pair_counts = _cache["cooccurrence"]
    labels    = _cache.get("product_labels", {})
    df        = recommend_for_product(product_id, item_counts, pair_counts, top_n)
    base_label = labels.get(product_id, f"Product {product_id}")
    if df.empty:
        return {"product_id": product_id, "product_label": base_label, "recommendations": []}
    return {
        "product_id":    product_id,
        "product_label": base_label,
        "recommendations": [
            {
                "product_id": int(r["product_id"]),
                "label":      labels.get(int(r["product_id"]), f"Product {int(r['product_id'])}"),
                "support":    int(r["support"]),
                "confidence": round(float(r["confidence"]), 4),
            }
            for _, r in df.iterrows()
        ],
    }


@app.get("/api/recomendar/cliente")
def recomendar_cliente(
    customer_id: str = Query(..., description="ID del cliente"),
    top_n:       int = Query(10, ge=1, le=20),
) -> dict:
    if "cooccurrence" not in _cache:
        raise HTTPException(status_code=503, detail="Datos no disponibles.")
    items                    = _cache["data"]["items"]
    item_counts, pair_counts = _cache["cooccurrence"]
    labels = _cache.get("product_labels", {})
    df     = recommend_for_customer(customer_id, items, item_counts, pair_counts, top_n)
    if df.empty:
        return {"customer_id": customer_id, "recommendations": []}
    return {
        "customer_id": customer_id,
        "recommendations": [
            {
                "product_id": int(r["product_id"]),
                "label":      labels.get(int(r["product_id"]), f"Product {int(r['product_id'])}"),
                "support":    int(r["support"]),
                "score":      round(float(r["score"]), 4),
            }
            for _, r in df.iterrows()
        ],
    }


@app.post("/api/reload")
def reload_data() -> dict:
    """
    Recarga los datos desde DATA_DIR y recomputa todos los caches.
    Implementa el requisito C: 'Generacion de nuevos resultados' al incorporar
    nuevos archivos CSV en la carpeta de Transactions.
    """
    global _cache
    try:
        print("Recargando datos desde", DATA_DIR)
        data      = load_data(DATA_DIR)
        _cache    = _build_cache(data)
        kpis      = _cache["kpis"]
        print("Recarga completada.")
        return {
            "status":       "ok",
            "transactions": int(kpis["total_transactions"]),
            "units":        int(kpis["total_units"]),
            "products":     len(_cache["product_ids"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
