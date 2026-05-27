from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics import (
    build_cooccurrence,
    build_customer_features,
    build_product_labels,
    compute_kpis,
    recommend_for_customer,
    recommend_for_product,
    run_kmeans,
)
from src.data_loader import load_data

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "DataSet" / "DataSet"

st.set_page_config(page_title="Supermarket Transactions Analytics", layout="wide")

CUSTOM_CSS = """
<style>
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap");
html, body, [class*="css"] {
    font-family: "Space Grotesk", sans-serif;
}
.stApp {
    background: radial-gradient(circle at 15% 20%, #f2f2ff 0%, #ffffff 40%, #f5fff8 100%);
}
.section-title {
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: 0.3px;
}
.kpi-card {
    border: 1px solid #e3e3f1;
    border-radius: 12px;
    padding: 12px 16px;
    background: #ffffffcc;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.title("Analisis y Modelado de Transacciones")
st.caption("Dashboard funcional para analisis descriptivo, diagnostico y modelos basicos.")

with st.sidebar:
    st.header("Configuracion")
    data_dir_input = st.text_input("Ruta de datos", str(DEFAULT_DATA_DIR))
    min_support = st.slider("Min soporte por producto", min_value=5, max_value=200, value=30, step=5)
    top_n_reco = st.slider("Top N recomendaciones", min_value=3, max_value=20, value=10, step=1)
    if st.button("Recargar datos"):
        st.cache_data.clear()


@st.cache_data(show_spinner=False)
def load_all(base_dir: Path) -> dict:
    return load_data(base_dir)


try:
    data = load_all(Path(data_dir_input))
except FileNotFoundError:
    st.error("No se encontro la ruta de datos. Verifica la carpeta DataSet.")
    st.stop()
except Exception as exc:
    st.error(f"Error al cargar datos: {exc}")
    st.stop()

transactions = data["transactions"]
items = data["items"]

if transactions.empty or items.empty:
    st.warning("No se encontraron transacciones para analizar.")
    st.stop()

kpis = compute_kpis(transactions, items)
product_labels = build_product_labels(items)

st.markdown('<div class="section-title">Resumen Ejecutivo</div>', unsafe_allow_html=True)
metric_cols = st.columns(2)
metric_cols[0].metric("Total unidades vendidas", f"{kpis['total_units']:,}")
metric_cols[1].metric("Numero de transacciones", f"{kpis['total_transactions']:,}")

st.info(
    "Nota: El dataset no incluye monto ni precio. Las metricas usan volumen y frecuencia. "
    "El campo de cliente se infiere de la tercera columna de transacciones."
)

col_a, col_b = st.columns(2)
with col_a:
    fig_top_products = px.bar(
        kpis["top_products"],
        x="units",
        y="label",
        orientation="h",
        title="Top 10 productos por volumen",
    )
    st.plotly_chart(fig_top_products, use_container_width=True)

with col_b:
    fig_top_customers = px.bar(
        kpis["top_customers"],
        x="transactions",
        y="customer_label",
        orientation="h",
        title="Top 10 clientes por compras",
    )
    st.plotly_chart(fig_top_customers, use_container_width=True)

col_c, col_d = st.columns(2)
with col_c:
    fig_peak_days = px.line(
        kpis["transactions_per_day"],
        x="date",
        y="transactions",
        title="Dias pico de compra (transacciones)",
    )
    st.plotly_chart(fig_peak_days, use_container_width=True)

with col_d:
    fig_categories = px.bar(
        kpis["category_units"],
        x="units",
        y="category_name",
        orientation="h",
        title="Categorias mas rentables (volumen relativo)",
    )
    st.plotly_chart(fig_categories, use_container_width=True)

st.markdown('<div class="section-title">Visualizaciones Analiticas</div>', unsafe_allow_html=True)
col_e, col_f = st.columns(2)
with col_e:
    fig_sales_time = px.line(
        kpis["units_per_day"],
        x="date",
        y="units",
        title="Ventas por dia (unidades)",
    )
    st.plotly_chart(fig_sales_time, use_container_width=True)

with col_f:
    fig_box = px.box(
        kpis["customer_units"],
        y="total_units",
        title="Distribucion de unidades por cliente",
    )
    st.plotly_chart(fig_box, use_container_width=True)

if kpis["customer_corr"].empty:
    st.info("No hay suficientes datos para la correlacion.")
else:
    fig_heatmap = px.imshow(
        kpis["customer_corr"],
        text_auto=".2f",
        aspect="auto",
        title="Heatmap de correlacion (metricas por cliente)",
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown('<div class="section-title">Analisis Avanzado</div>', unsafe_allow_html=True)
features = build_customer_features(transactions, items)
if features.empty:
    st.warning("No hay suficientes datos para segmentacion.")
else:
    k = st.slider("Numero de clusters (K-Means)", min_value=2, max_value=8, value=4, step=1)
    clustered, cluster_summary = run_kmeans(features, k)
    fig_cluster = px.scatter(
        clustered,
        x="pca1",
        y="pca2",
        color="cluster",
        title="Segmentacion de clientes (PCA 2D)",
        hover_data=["customer_id", "frequency", "total_units", "unique_products", "unique_categories"],
    )
    st.plotly_chart(fig_cluster, use_container_width=True)
    st.subheader("Descripcion de clusters")
    st.dataframe(cluster_summary, use_container_width=True)

st.markdown("### Recomendador de productos")


@st.cache_data(show_spinner=False)
def get_cooccurrence(items_df: pd.DataFrame, min_support_value: int):
    return build_cooccurrence(items_df, min_support_value)


item_counts, pair_counts = get_cooccurrence(items, min_support)

tab_product, tab_customer = st.tabs(["Por producto", "Por cliente"])

with tab_product:
    product_ids = sorted(int(pid) for pid in items["product_id"].dropna().unique().tolist())
    selected_product = st.selectbox(
        "Producto base",
        product_ids,
        format_func=lambda pid: product_labels.get(pid, f"Product {pid}"),
    )
    rec_prod = recommend_for_product(selected_product, item_counts, pair_counts, top_n_reco)
    if rec_prod.empty:
        st.info("No hay recomendaciones para este producto con el soporte actual.")
    else:
        rec_prod["label"] = rec_prod["product_id"].map(lambda pid: product_labels.get(pid, f"Product {pid}"))
        st.dataframe(rec_prod[["label", "support", "confidence"]], use_container_width=True)

with tab_customer:
    customer_ids = sorted(transactions["customer_id"].dropna().unique().tolist())
    selected_customer = st.selectbox("Cliente", customer_ids)
    rec_cust = recommend_for_customer(selected_customer, items, item_counts, pair_counts, top_n_reco)
    if rec_cust.empty:
        st.info("No hay recomendaciones para este cliente con el soporte actual.")
    else:
        rec_cust["label"] = rec_cust["product_id"].map(lambda pid: product_labels.get(pid, f"Product {pid}"))
        st.dataframe(rec_cust[["label", "support", "score"]], use_container_width=True)
