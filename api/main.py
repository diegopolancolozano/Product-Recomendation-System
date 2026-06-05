"""
FastAPI backend — Supermarket Analytics API.
Corresponde al contenedor "Cloud Run — FastAPI" del diagrama GCP.

Modo de operacion:
  - Si CLOUD_SQL_INSTANCE esta definido → lee de Cloud SQL (PostgreSQL)
  - Si no → lee de CSV (desarrollo local)

Endpoints:
  GET /api/health
  GET /api/resumen
  GET /api/visualizaciones
  GET /api/patrones
  GET /api/avanzado
  GET /api/recomendar/producto
  GET /api/recomendar/cliente
  POST /api/reload
"""
from __future__ import annotations

import math
import os
import threading
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Modo de operacion ─────────────────────────────────────────────────────────
CLOUD_SQL_INSTANCE = os.getenv("CLOUD_SQL_INSTANCE", "")
USE_CLOUD_SQL      = bool(CLOUD_SQL_INSTANCE)
DATA_DIR           = Path(os.getenv("DATA_DIR", str(ROOT / "DataSet" / "DataSet")))

app = FastAPI(title="Supermarket Analytics API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

_cache: dict[str, Any] = {}


# ── Conexion a Cloud SQL ──────────────────────────────────────────────────────
def _get_sql_engine():
    """Crea un engine SQLAlchemy conectado a Cloud SQL via Cloud SQL Python Connector."""
    from google.cloud.sql.connector import Connector
    import sqlalchemy

    connector = Connector()
    db_user   = os.environ["DB_USER"]
    db_pass   = os.environ["DB_PASSWORD"]

    def getconn():
        return connector.connect(
            CLOUD_SQL_INSTANCE, "pg8000",
            user=db_user, password=db_pass, db="analitica",
        )

    return sqlalchemy.create_engine(
        "postgresql+pg8000://", creator=getconn,
        pool_size=2, max_overflow=0,
    )


def _query(sql: str) -> pd.DataFrame:
    """Ejecuta una query en Cloud SQL y devuelve un DataFrame."""
    engine = _get_sql_engine()
    with engine.connect() as conn:
        return pd.read_sql(sql, conn)


# ── Carga desde Cloud SQL ─────────────────────────────────────────────────────
def _load_from_cloud_sql() -> dict:
    print("Cargando datos desde Cloud SQL...")

    kpis_row = _query("SELECT total_units, total_transactions FROM analitica.kpis ORDER BY computed_at DESC LIMIT 1")
    top_products = _query("SELECT rank, product_id, category_name, units FROM analitica.top_products ORDER BY rank")
    top_customers = _query("SELECT rank, customer_id, transactions FROM analitica.top_customers ORDER BY rank")
    units_per_day = _query("SELECT date, units FROM analitica.units_per_day ORDER BY date")
    transactions_per_day = _query("SELECT date, transactions FROM analitica.transactions_per_day ORDER BY date")
    category_units = _query("SELECT rank, category_name, units FROM analitica.category_units ORDER BY rank")
    customer_units = _query("SELECT customer_id, total_units FROM analitica.customer_units")
    customer_features = _query("SELECT * FROM analitica.customer_features")
    weekday_patterns = _query("SELECT * FROM analitica.weekday_patterns ORDER BY weekday")
    store_patterns = _query("SELECT * FROM analitica.store_patterns ORDER BY transactions DESC")
    freq_histogram = _query("SELECT bucket, customers FROM analitica.freq_histogram")

    corr_df = pd.DataFrame()
    if not customer_features.empty:
        feat_cols = ["frequency", "total_units", "unique_products", "unique_categories", "avg_basket_size"]
        available = [c for c in feat_cols if c in customer_features.columns]
        corr_df = customer_features[available].corr() if available else pd.DataFrame()

    # ML resultados
    engine_ml = _get_sql_engine()
    with engine_ml.connect() as conn:
        import sqlalchemy
        clusters_df = pd.read_sql("SELECT * FROM ml_resultados.customer_clusters", conn)
        profiles_df = pd.read_sql("SELECT * FROM ml_resultados.cluster_profiles ORDER BY cluster", conn)
        rules_df    = pd.read_sql("SELECT * FROM ml_resultados.association_rules", conn)

    return {
        "source": "cloud_sql",
        "kpis": {
            "total_units":         int(kpis_row["total_units"].iloc[0]) if not kpis_row.empty else 0,
            "total_transactions":  int(kpis_row["total_transactions"].iloc[0]) if not kpis_row.empty else 0,
            "top_products":        top_products,
            "top_customers":       top_customers,
            "units_per_day":       units_per_day,
            "transactions_per_day": transactions_per_day,
            "category_units":      category_units,
            "customer_units":      customer_units,
            "customer_corr":       corr_df,
        },
        "patterns": {
            "weekday":   weekday_patterns,
            "store":     store_patterns,
            "freq_hist": freq_histogram,
        },
        "ml": {
            "clusters": clusters_df,
            "profiles": profiles_df,
            "rules":    rules_df,
        },
    }


# ── Carga desde CSV (modo local) ──────────────────────────────────────────────
def _load_from_csv() -> dict:
    from src.analytics import (
        build_cooccurrence, build_customer_features, build_product_labels,
        compute_kpis, compute_patterns, run_kmeans,
    )
    from src.data_loader import load_data

    print("[1/5] Cargando CSV...")
    data = load_data(DATA_DIR)
    transactions = data["transactions"]
    items        = data["items"]
    print(f"      {len(transactions):,} transacciones | {len(items):,} items")

    print("[2/5] KPIs y patrones...")
    kpis     = compute_kpis(transactions, items)
    patterns = compute_patterns(transactions, items)

    print("[3/5] Features y K-Means...")
    features = build_customer_features(transactions, items)
    clustered, summary = run_kmeans(features, k=4)
    cluster_sizes = clustered["cluster"].value_counts().to_dict() if not clustered.empty else {}

    print("[4/5] Co-ocurrencia, etiquetas e historial de clientes...")
    item_counts, pair_counts = build_cooccurrence(items, min_item_support=30)
    product_labels = build_product_labels(items)
    customer_ids   = sorted(transactions["customer_id"].dropna().unique().tolist())[:2000]

    # Historial compacto por cliente (reemplaza items DataFrame de 15M filas)
    customer_products: dict = (
        items.groupby("customer_id")["product_id"]
        .apply(lambda s: set(int(p) for p in s.dropna()))
        .to_dict()
    )

    print("[5/5] Liberando DataFrames y guardando cache...")
    import gc
    del items
    del transactions
    del data
    del features
    gc.collect()

    return {
        "source":            "csv",
        "kpis":              kpis,
        "patterns_raw":      patterns,
        "kmeans":            {"clustered": clustered, "summary": summary, "cluster_sizes": cluster_sizes},
        "cooccurrence":      (item_counts, pair_counts),
        "product_labels":    product_labels,
        "product_ids":       sorted(item_counts.keys()),
        "customer_ids":      customer_ids,
        "customer_products": customer_products,
    }


_loading = True
_load_error: str | None = None


def _rebuild_cache() -> None:
    global _cache, _loading, _load_error
    if USE_CLOUD_SQL:
        _cache = _load_from_cloud_sql()
    else:
        _cache = _load_from_csv()
    print("Cache listo.")


@app.on_event("startup")
def startup_event() -> None:
    """
    Carga datos en un hilo de fondo para que Cloud Run no mate el contenedor
    por timeout del health check. El endpoint /api/health devuelve 200 de
    inmediato; los demas endpoints retornan 503 hasta que la carga termine.
    """
    def _load():
        global _loading, _load_error
        try:
            _rebuild_cache()
        except Exception as exc:
            _load_error = str(exc)
            print(f"Error en carga: {exc}")
        finally:
            _loading = False

    threading.Thread(target=_load, daemon=True).start()


# ── Utilidades ────────────────────────────────────────────────────────────────
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


def _require(key: str):
    if not _cache:
        raise HTTPException(status_code=503, detail="Datos no disponibles.")
    return _cache.get(key)


# ── Helpers para serializar segun la fuente ───────────────────────────────────
def _get_kpis():
    if USE_CLOUD_SQL:
        return _cache["kpis"]
    return _cache["kpis"]


def _top_products_list() -> list[dict]:
    kpis = _get_kpis()
    df   = kpis["top_products"]
    if USE_CLOUD_SQL:
        labels = {int(r["product_id"]): f"Product {int(r['product_id'])} ({r['category_name']})"
                  for _, r in df.iterrows()}
        return [{"product_id": int(r["product_id"]),
                 "label": labels.get(int(r["product_id"]), f"Product {int(r['product_id'])}"),
                 "units": int(r["units"])}
                for _, r in df.iterrows()]
    labels = _cache.get("product_labels", {})
    return [{"product_id": int(r["product_id"]),
             "label": labels.get(int(r["product_id"]), f"Product {int(r['product_id'])}"),
             "units": int(r["units"])}
            for _, r in df.iterrows()]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health() -> dict:
    # Siempre retorna 200 para que Cloud Run no mate el contenedor.
    # El campo "status" indica si los datos ya estan listos.
    kpis = _cache.get("kpis", {}) if not USE_CLOUD_SQL else {}
    return {
        "status":       "loading" if _loading else ("error" if _load_error else "ok"),
        "source":       _cache.get("source", "none"),
        "data_loaded":  bool(_cache),
        "transactions": kpis.get("total_transactions", 0) if not USE_CLOUD_SQL
                        else _cache.get("kpis", {}).get("total_transactions", 0),
    }


@app.get("/api/resumen")
def get_resumen() -> dict:
    if not _cache:
        raise HTTPException(status_code=503, detail="Datos no disponibles.")
    kpis = _cache["kpis"]

    if USE_CLOUD_SQL:
        top_products = [
            {"product_id": int(r["product_id"]),
             "label": f"Product {int(r['product_id'])} ({r['category_name']})",
             "units": int(r["units"])}
            for _, r in kpis["top_products"].iterrows()
        ]
        top_customers = [
            {"customer_id": str(r["customer_id"]),
             "label": f"Customer {r['customer_id']}",
             "transactions": int(r["transactions"])}
            for _, r in kpis["top_customers"].iterrows()
        ]
        transactions_per_day = [
            {"date": str(r["date"]), "transactions": int(r["transactions"])}
            for _, r in kpis["transactions_per_day"].iterrows()
        ]
        category_units = [
            {"category_name": str(r["category_name"]), "units": int(r["units"])}
            for _, r in kpis["category_units"].iterrows()
        ]
        total_units        = kpis["total_units"]
        total_transactions = kpis["total_transactions"]
    else:
        labels = _cache.get("product_labels", {})
        top_products = [
            {"product_id": int(r["product_id"]),
             "label": labels.get(int(r["product_id"]), f"Product {int(r['product_id'])}"),
             "units": int(r["units"])}
            for _, r in kpis["top_products"].iterrows()
        ]
        top_customers = [
            {"customer_id": str(r["customer_id"]),
             "label": str(r["customer_label"]),
             "transactions": int(r["transactions"])}
            for _, r in kpis["top_customers"].iterrows()
        ]
        transactions_per_day = [
            {"date": str(r["date"]), "transactions": int(r["transactions"])}
            for _, r in kpis["transactions_per_day"].iterrows()
        ]
        category_units = [
            {"category_name": str(r["category_name"]), "units": int(r["units"])}
            for _, r in kpis["category_units"].iterrows()
        ]
        total_units        = int(kpis["total_units"])
        total_transactions = int(kpis["total_transactions"])

    return {
        "total_units":          total_units,
        "total_transactions":   total_transactions,
        "top_products":         top_products,
        "top_customers":        top_customers,
        "transactions_per_day": transactions_per_day,
        "category_units":       category_units,
    }


@app.get("/api/visualizaciones")
def get_visualizaciones() -> dict:
    if not _cache:
        raise HTTPException(status_code=503, detail="Datos no disponibles.")
    kpis = _cache["kpis"]

    units_per_day = [
        {"date": str(r["date"]), "units": int(r["units"])}
        for _, r in kpis["units_per_day"].iterrows()
    ]
    boxplot     = _boxplot_stats(kpis["customer_units"]["total_units"])
    corr_df     = kpis["customer_corr"]
    corr_matrix: list[dict] = []
    corr_labels: list[str]  = []
    if not corr_df.empty:
        corr_labels = [str(c) for c in corr_df.columns.tolist()]
        for rn in corr_df.index:
            for cn in corr_df.columns:
                v = _safe_float(corr_df.loc[rn, cn]) or 0.0
                corr_matrix.append({"x": str(cn), "y": str(rn), "value": round(v, 3)})

    return {
        "units_per_day":      units_per_day,
        "boxplot":            boxplot,
        "correlation_matrix": corr_matrix,
        "correlation_labels": corr_labels,
    }


@app.get("/api/patrones")
def get_patrones() -> dict:
    if not _cache:
        raise HTTPException(status_code=503, detail="Datos no disponibles.")

    if USE_CLOUD_SQL:
        p = _cache["patterns"]
        by_weekday = [
            {"weekday": int(r["weekday"]), "day_name": str(r["day_name"]),
             "avg_transactions": float(r["avg_transactions"]),
             "avg_units": float(r["avg_units"]),
             "total_transactions": int(r["total_transactions"])}
            for _, r in p["weekday"].iterrows()
        ]
        by_store = [
            {"store_id": str(r["store_id"]),
             "transactions": int(r["transactions"]), "units": int(r["units"])}
            for _, r in p["store"].iterrows()
        ]
        freq_histogram = [
            {"bucket": str(r["bucket"]), "customers": int(r["customers"])}
            for _, r in p["freq_hist"].iterrows()
        ]
        return {
            "by_weekday":    by_weekday,
            "by_store":      by_store,
            "num_stores":    len(by_store),
            "freq_histogram": freq_histogram,
        }
    else:
        return _cache["patterns_raw"]


@app.get("/api/avanzado")
def get_avanzado() -> dict:
    if not _cache:
        raise HTTPException(status_code=503, detail="Datos no disponibles.")

    if USE_CLOUD_SQL:
        ml = _cache["ml"]
        clusters_df = ml["clusters"]
        profiles_df = ml["profiles"]
        rules_df    = ml["rules"]

        sample = clusters_df.sample(min(4000, len(clusters_df)), random_state=42) \
                 if len(clusters_df) > 4000 else clusters_df

        scatter = [
            {"customer_id": str(r["customer_id"]),
             "pca1": round(float(r["pca1"]), 4), "pca2": round(float(r["pca2"]), 4),
             "cluster": int(r["cluster"]), "frequency": int(r["frequency"]),
             "total_units": int(r["total_units"]), "unique_products": int(r["unique_products"]),
             "avg_basket_size": round(float(r["avg_basket_size"]), 1)}
            for _, r in sample.iterrows()
        ]
        cluster_summary = [
            {"cluster": int(r["cluster"]), "frequency": round(float(r["frequency"]), 2),
             "total_units": round(float(r["total_units"]), 2),
             "unique_products": round(float(r["unique_products"]), 2),
             "unique_categories": round(float(r["unique_categories"]), 2),
             "avg_basket_size": round(float(r["avg_basket_size"]), 2),
             "size": int(r["size"])}
            for _, r in profiles_df.iterrows()
        ]
        # Productos del recomendador desde reglas
        product_ids = sorted(rules_df["antecedent"].dropna().unique().tolist())
        product_options = [{"product_id": int(p), "label": f"Product {int(p)}"} for p in product_ids[:500]]
        customer_ids_list = []

    else:
        kmeans = _cache["kmeans"]
        clustered = kmeans["clustered"]
        summary   = kmeans["summary"]
        cluster_sizes = kmeans["cluster_sizes"]
        labels    = _cache.get("product_labels", {})

        sample = clustered.sample(4000, random_state=42) \
                 if len(clustered) > 4000 else clustered

        scatter = [
            {"customer_id": str(r["customer_id"]),
             "pca1": round(float(r["pca1"]), 4), "pca2": round(float(r["pca2"]), 4),
             "cluster": int(r["cluster"]), "frequency": int(r["frequency"]),
             "total_units": int(r["total_units"]), "unique_products": int(r["unique_products"]),
             "avg_basket_size": round(float(r["avg_basket_size"]), 1)}
            for _, r in sample.iterrows()
        ]
        cluster_summary = [
            {"cluster": int(r["cluster"]), "frequency": round(float(r["frequency"]), 2),
             "total_units": round(float(r["total_units"]), 2),
             "unique_products": round(float(r["unique_products"]), 2),
             "unique_categories": round(float(r["unique_categories"]), 2),
             "avg_basket_size": round(float(r["avg_basket_size"]), 2),
             "size": int(cluster_sizes.get(int(r["cluster"]), 0))}
            for _, r in summary.iterrows()
        ]
        product_options = [
            {"product_id": pid, "label": labels.get(pid, f"Product {pid}")}
            for pid in _cache.get("product_ids", [])
        ]
        customer_ids_list = _cache.get("customer_ids", [])[:500]

    return {
        "scatter":         scatter,
        "cluster_summary": cluster_summary,
        "k":               len(cluster_summary),
        "product_options": product_options,
        "customer_ids":    customer_ids_list,
    }


@app.get("/api/recomendar/producto")
def recomendar_producto(
    product_id: int = Query(...),
    top_n:      int = Query(10, ge=1, le=20),
) -> dict:
    if not _cache:
        raise HTTPException(status_code=503, detail="Datos no disponibles.")

    if USE_CLOUD_SQL:
        rules = _cache["ml"]["rules"]
        recs  = (
            rules[rules["antecedent"] == product_id]
            .sort_values("confidence", ascending=False)
            .head(top_n)
        )
        return {
            "product_id":    product_id,
            "product_label": f"Product {product_id}",
            "recommendations": [
                {"product_id": int(r["consequent"]),
                 "label": f"Product {int(r['consequent'])}",
                 "support": round(float(r["support"]), 4),
                 "confidence": round(float(r["confidence"]), 4)}
                for _, r in recs.iterrows()
            ],
        }
    else:
        from src.analytics import recommend_for_product
        item_counts, pair_counts = _cache["cooccurrence"]
        labels = _cache.get("product_labels", {})
        df = recommend_for_product(product_id, item_counts, pair_counts, top_n)
        base_label = labels.get(product_id, f"Product {product_id}")
        if df.empty:
            return {"product_id": product_id, "product_label": base_label, "recommendations": []}
        return {
            "product_id": product_id, "product_label": base_label,
            "recommendations": [
                {"product_id": int(r["product_id"]),
                 "label": labels.get(int(r["product_id"]), f"Product {int(r['product_id'])}"),
                 "support": int(r["support"]),
                 "confidence": round(float(r["confidence"]), 4)}
                for _, r in df.iterrows()
            ],
        }


@app.get("/api/recomendar/cliente")
def recomendar_cliente(
    customer_id: str = Query(...),
    top_n:       int = Query(10, ge=1, le=20),
) -> dict:
    if not _cache:
        raise HTTPException(status_code=503, detail="Datos no disponibles.")

    if USE_CLOUD_SQL:
        rules    = _cache["ml"]["rules"]
        clusters = _cache["ml"]["clusters"]
        cust_row = clusters[clusters["customer_id"] == str(customer_id)]
        if cust_row.empty:
            return {"customer_id": customer_id, "recommendations": []}
        # Productos comprados por el cliente (desde staging via query directa)
        bought_df = _query(
            f"SELECT DISTINCT product_id FROM staging.items WHERE customer_id = '{customer_id}'"
        )
        bought = set(bought_df["product_id"].tolist()) if not bought_df.empty else set()
        recs = (
            rules[rules["antecedent"].isin(bought) & ~rules["consequent"].isin(bought)]
            .sort_values("confidence", ascending=False)
            .drop_duplicates(subset=["consequent"])
            .head(top_n)
        )
        return {
            "customer_id": customer_id,
            "recommendations": [
                {"product_id": int(r["consequent"]),
                 "label": f"Product {int(r['consequent'])}",
                 "support": round(float(r["support"]), 4),
                 "score": round(float(r["confidence"]), 4)}
                for _, r in recs.iterrows()
            ],
        }
    else:
        # Usar el dict compacto de historial en vez del DataFrame de 15M filas
        item_counts, pair_counts = _cache["cooccurrence"]
        labels           = _cache.get("product_labels", {})
        customer_products = _cache.get("customer_products", {})
        bought = customer_products.get(str(customer_id), set())
        if not bought:
            return {"customer_id": customer_id, "recommendations": []}

        scores: dict[int, float] = {}
        supports: dict[int, int] = {}
        for (a, b), count in pair_counts.items():
            if a in bought and b not in bought:
                base, other = a, b
            elif b in bought and a not in bought:
                base, other = b, a
            else:
                continue
            if base not in item_counts:
                continue
            score = count / item_counts[base]
            scores[other] = scores.get(other, 0.0) + score
            supports[other] = supports.get(other, 0) + int(count)

        if not scores:
            return {"customer_id": customer_id, "recommendations": []}

        top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return {
            "customer_id": customer_id,
            "recommendations": [
                {"product_id": pid,
                 "label": labels.get(pid, f"Product {pid}"),
                 "support": supports.get(pid, 0),
                 "score": round(score, 4)}
                for pid, score in top
            ],
        }


@app.post("/api/reload")
def reload_data() -> dict:
    """
    Recarga los datos y recomputa el cache.
    En produccion GCP, los datos ya fueron procesados por Dataproc
    y escritos en Cloud SQL — solo se refresca el cache en memoria.
    En modo local, recarga los CSV.
    """
    try:
        _rebuild_cache()
        kpis = _cache.get("kpis", {})
        total = kpis.get("total_transactions", 0) if not USE_CLOUD_SQL else kpis.get("total_transactions", 0)
        return {"status": "ok", "source": _cache.get("source"), "transactions": total}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
