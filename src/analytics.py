from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = [
    "frequency",
    "total_units",
    "unique_products",
    "unique_categories",
    "avg_basket_size",
]


def build_product_labels(items: pd.DataFrame) -> Dict[int, str]:
    labels: Dict[int, str] = {}
    if items.empty:
        return labels

    mapping = (
        items[["product_id", "category_name"]]
        .dropna()
        .drop_duplicates()
        .groupby("product_id")["category_name"]
        .agg(lambda s: s.mode().iat[0] if not s.mode().empty else "Unknown")
    )
    for product_id, category_name in mapping.items():
        try:
            product_key = int(product_id)
        except (TypeError, ValueError):
            continue
        labels[product_key] = f"Product {product_key} ({category_name})"
    return labels


def compute_kpis(transactions: pd.DataFrame, items: pd.DataFrame) -> Dict[str, pd.DataFrame | int]:
    total_units = int(items.shape[0])
    total_transactions = int(transactions["transaction_uid"].nunique())

    labels = build_product_labels(items)

    top_products = (
        items.groupby("product_id")["transaction_uid"]
        .count()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="units")
    )
    top_products["label"] = top_products["product_id"].map(
        lambda pid: labels.get(int(pid), f"Product {pid}")
    )

    top_customers = (
        transactions.groupby("customer_id")["transaction_uid"]
        .nunique()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="transactions")
    )
    top_customers["customer_label"] = top_customers["customer_id"].map(lambda cid: f"Customer {cid}")

    transactions_per_day = (
        transactions.dropna(subset=["date"])
        .groupby(transactions["date"].dt.date)["transaction_uid"]
        .nunique()
        .reset_index(name="transactions")
        .rename(columns={"date": "date"})
        .sort_values("date")
    )

    units_per_day = (
        items.dropna(subset=["date"])
        .groupby(items["date"].dt.date)["product_id"]
        .count()
        .reset_index(name="units")
        .rename(columns={"date": "date"})
        .sort_values("date")
    )

    category_units = (
        items.groupby("category_name")["product_id"]
        .count()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="units")
    )

    customer_units = (
        items.groupby("customer_id")["product_id"]
        .count()
        .reset_index(name="total_units")
    )

    customer_features = build_customer_features(transactions, items)
    customer_corr = (
        customer_features[FEATURE_COLUMNS].corr() if not customer_features.empty else pd.DataFrame()
    )

    return {
        "total_units": total_units,
        "total_transactions": total_transactions,
        "top_products": top_products,
        "top_customers": top_customers,
        "transactions_per_day": transactions_per_day,
        "units_per_day": units_per_day,
        "category_units": category_units,
        "customer_units": customer_units,
        "customer_corr": customer_corr,
    }


def build_customer_features(transactions: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    if transactions.empty or items.empty:
        return pd.DataFrame()

    frequency = (
        transactions.groupby("customer_id")["transaction_uid"]
        .nunique()
        .rename("frequency")
    )
    total_units = items.groupby("customer_id")["product_id"].count().rename("total_units")
    unique_products = (
        items.groupby("customer_id")["product_id"].nunique().rename("unique_products")
    )
    unique_categories = (
        items.groupby("customer_id")["category_id"].nunique().rename("unique_categories")
    )

    features = pd.concat([frequency, total_units, unique_products, unique_categories], axis=1).fillna(0)
    features["avg_basket_size"] = (
        features["total_units"] / features["frequency"].replace(0, np.nan)
    ).fillna(0)
    features = features.reset_index().rename(columns={"customer_id": "customer_id"})
    return features


def run_kmeans(features: pd.DataFrame, k: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if features.empty:
        return features, pd.DataFrame()

    X = features[FEATURE_COLUMNS].astype(float).to_numpy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = model.fit_predict(X_scaled)

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X_scaled)

    clustered = features.copy()
    clustered["cluster"] = labels
    clustered["pca1"] = coords[:, 0]
    clustered["pca2"] = coords[:, 1]

    summary = clustered.groupby("cluster")[FEATURE_COLUMNS].mean().round(2).reset_index()
    return clustered, summary


WEEKDAY_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def compute_patterns(transactions: pd.DataFrame, items: pd.DataFrame) -> dict:
    """
    Patrones temporales y espaciales derivados de las columnas ya cargadas.

    Retorna:
      by_weekday  — promedio diario de transacciones y unidades por día de semana
      by_store    — volumen total de transacciones y unidades por store_id
      freq_hist   — histograma de frecuencia de compra por cliente
    """
    result: dict = {}

    # ── Día de la semana ──────────────────────────────────────────────────────
    if not transactions.empty and "date" in transactions.columns:
        t = transactions.dropna(subset=["date"]).copy()
        t["weekday"] = t["date"].dt.dayofweek          # 0=Lunes … 6=Domingo
        t["date_only"] = t["date"].dt.date

        # Contar cuántos días distintos caen en cada weekday (para el promedio)
        days_per_wd = (
            t[["weekday", "date_only"]]
            .drop_duplicates()
            .groupby("weekday")["date_only"]
            .count()
            .rename("num_days")
        )

        txn_per_wd = (
            t.groupby("weekday")["transaction_uid"]
            .nunique()
            .rename("total_transactions")
        )

        wd_df = pd.concat([txn_per_wd, days_per_wd], axis=1).fillna(0)
        wd_df["avg_transactions"] = (
            wd_df["total_transactions"] / wd_df["num_days"].replace(0, np.nan)
        ).fillna(0).round(1)

        # Unidades por día de semana (promedio diario)
        if not items.empty and "date" in items.columns:
            it = items.dropna(subset=["date"]).copy()
            it["weekday"] = it["date"].dt.dayofweek
            units_per_wd = it.groupby("weekday")["product_id"].count().rename("total_units")
            wd_df = wd_df.join(units_per_wd, how="left").fillna(0)
            wd_df["avg_units"] = (
                wd_df["total_units"] / wd_df["num_days"].replace(0, np.nan)
            ).fillna(0).round(1)
        else:
            wd_df["avg_units"] = 0.0

        result["by_weekday"] = [
            {
                "weekday": int(idx),
                "day_name": WEEKDAY_ES[int(idx)],
                "avg_transactions": float(row["avg_transactions"]),
                "avg_units": float(row["avg_units"]),
                "total_transactions": int(row["total_transactions"]),
            }
            for idx, row in wd_df.sort_index().iterrows()
            if 0 <= int(idx) <= 6
        ]
    else:
        result["by_weekday"] = []

    # ── Por tienda ────────────────────────────────────────────────────────────
    if not transactions.empty and "store_id" in transactions.columns:
        store_txn = (
            transactions.groupby("store_id")["transaction_uid"]
            .nunique()
            .sort_values(ascending=False)
            .reset_index(name="transactions")
        )
        store_units = pd.Series(dtype="int64")
        if not items.empty and "store_id" in items.columns:
            store_units = (
                items.groupby("store_id")["product_id"]
                .count()
                .rename("units")
            )

        store_df = store_txn.set_index("store_id")
        store_df = store_df.join(store_units, how="left").fillna(0).reset_index()
        store_df["units"] = store_df["units"].astype(int)

        result["by_store"] = [
            {
                "store_id": str(row["store_id"]),
                "transactions": int(row["transactions"]),
                "units": int(row["units"]),
            }
            for _, row in store_df.head(20).iterrows()
        ]
        result["num_stores"] = int(len(store_df))
    else:
        result["by_store"] = []
        result["num_stores"] = 0

    # ── Histograma de frecuencia de compra ────────────────────────────────────
    if not transactions.empty:
        freq_series = (
            transactions.groupby("customer_id")["transaction_uid"]
            .nunique()
        )
        # Buckets: 1, 2, 3, 4, 5, 6-10, 11-20, 21+
        def bucket(n: int) -> str:
            if n <= 5:
                return str(n)
            if n <= 10:
                return "6-10"
            if n <= 20:
                return "11-20"
            return "21+"

        BUCKET_ORDER = ["1", "2", "3", "4", "5", "6-10", "11-20", "21+"]
        hist = freq_series.map(bucket).value_counts().rename("customers")
        hist_df = hist.reindex(BUCKET_ORDER, fill_value=0).reset_index()
        hist_df.columns = pd.Index(["bucket", "customers"])

        result["freq_histogram"] = [
            {"bucket": str(row["bucket"]), "customers": int(row["customers"])}
            for _, row in hist_df.iterrows()
        ]
    else:
        result["freq_histogram"] = []

    return result


def build_cooccurrence(
    items: pd.DataFrame, min_item_support: int = 20
) -> Tuple[Dict[int, int], Counter]:
    if items.empty:
        return {}, Counter()

    item_counts_series = items["product_id"].value_counts()
    allowed = set(item_counts_series[item_counts_series >= min_item_support].index.tolist())
    baskets = (
        items.groupby("transaction_uid")["product_id"]
        .apply(lambda s: sorted({int(p) for p in s.dropna() if p in allowed}))
        .tolist()
    )

    pair_counts: Counter = Counter()
    for products in baskets:
        if len(products) < 2:
            continue
        for a, b in combinations(products, 2):
            pair_counts[(a, b)] += 1

    item_counts = {
        int(product_id): int(count)
        for product_id, count in item_counts_series[item_counts_series >= min_item_support].to_dict().items()
    }
    return item_counts, pair_counts


def recommend_for_product(
    product_id: int, item_counts: Dict[int, int], pair_counts: Counter, top_n: int
) -> pd.DataFrame:
    if product_id not in item_counts:
        return pd.DataFrame()

    scores = []
    for (a, b), count in pair_counts.items():
        if a == product_id:
            other = b
        elif b == product_id:
            other = a
        else:
            continue
        confidence = count / item_counts[product_id]
        scores.append((other, int(count), float(confidence)))

    if not scores:
        return pd.DataFrame()

    df = pd.DataFrame(scores, columns=["product_id", "support", "confidence"])
    df = df.sort_values(["confidence", "support"], ascending=False).head(top_n)
    return df


def recommend_for_customer(
    customer_id: str,
    items: pd.DataFrame,
    item_counts: Dict[int, int],
    pair_counts: Counter,
    top_n: int,
) -> pd.DataFrame:
    if items.empty:
        return pd.DataFrame()

    customer_products = set(
        items.loc[items["customer_id"] == str(customer_id), "product_id"].dropna().astype(int)
    )
    if not customer_products:
        return pd.DataFrame()

    scores: Dict[int, float] = {}
    supports: Dict[int, int] = {}

    for (a, b), count in pair_counts.items():
        if a in customer_products and b not in customer_products:
            base = a
            other = b
        elif b in customer_products and a not in customer_products:
            base = b
            other = a
        else:
            continue

        if base not in item_counts:
            continue

        score = count / item_counts[base]
        scores[other] = scores.get(other, 0.0) + score
        supports[other] = supports.get(other, 0) + int(count)

    if not scores:
        return pd.DataFrame()

    rows = [(pid, supports.get(pid, 0), score) for pid, score in scores.items()]
    df = pd.DataFrame(rows, columns=["product_id", "support", "score"])
    df = df.sort_values(["score", "support"], ascending=False).head(top_n)
    return df
