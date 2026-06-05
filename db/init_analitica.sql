-- Schema analitica: metricas descriptivas y KPIs computados por Dataproc
-- Ejecutado una sola vez al crear la instancia Cloud SQL

CREATE SCHEMA IF NOT EXISTS analitica;
CREATE SCHEMA IF NOT EXISTS staging;

-- ── Staging: datos crudos normalizados por el job ETL ────────────────────────
CREATE TABLE IF NOT EXISTS staging.transactions (
    transaction_uid VARCHAR(100) PRIMARY KEY,
    date            DATE,
    store_id        VARCHAR(20),
    customer_id     VARCHAR(100),
    product_list    TEXT,
    source_file     VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS staging.items (
    id              BIGSERIAL PRIMARY KEY,
    transaction_uid VARCHAR(100),
    date            DATE,
    store_id        VARCHAR(20),
    customer_id     VARCHAR(100),
    product_id      BIGINT,
    category_id     BIGINT,
    category_name   VARCHAR(200)
);

CREATE INDEX IF NOT EXISTS idx_items_product    ON staging.items(product_id);
CREATE INDEX IF NOT EXISTS idx_items_customer   ON staging.items(customer_id);
CREATE INDEX IF NOT EXISTS idx_items_date       ON staging.items(date);

-- ── KPIs globales ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analitica.kpis (
    computed_at         TIMESTAMP DEFAULT NOW(),
    total_units         BIGINT,
    total_transactions  BIGINT
);

-- ── Top 10 productos por volumen ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analitica.top_products (
    rank          INTEGER,
    product_id    BIGINT,
    category_name VARCHAR(200),
    units         BIGINT
);

-- ── Top 10 clientes por transacciones ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analitica.top_customers (
    rank         INTEGER,
    customer_id  VARCHAR(100),
    transactions BIGINT
);

-- ── Unidades vendidas por dia ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analitica.units_per_day (
    date  DATE PRIMARY KEY,
    units BIGINT
);

-- ── Transacciones por dia ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analitica.transactions_per_day (
    date         DATE PRIMARY KEY,
    transactions BIGINT
);

-- ── Unidades por categoria ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analitica.category_units (
    rank          INTEGER,
    category_name VARCHAR(200),
    units         BIGINT
);

-- ── Unidades totales por cliente (para boxplot) ───────────────────────────────
CREATE TABLE IF NOT EXISTS analitica.customer_units (
    customer_id  VARCHAR(100) PRIMARY KEY,
    total_units  BIGINT
);

-- ── Patrones por dia de semana ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analitica.weekday_patterns (
    weekday           INTEGER PRIMARY KEY,
    day_name          VARCHAR(20),
    total_transactions BIGINT,
    avg_transactions  NUMERIC(10,1),
    avg_units         NUMERIC(10,1)
);

-- ── Patrones por tienda ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analitica.store_patterns (
    store_id     VARCHAR(20) PRIMARY KEY,
    transactions BIGINT,
    units        BIGINT
);

-- ── Histograma de frecuencia de compra ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS analitica.freq_histogram (
    bucket    VARCHAR(10) PRIMARY KEY,
    customers BIGINT
);

-- ── Correlacion entre variables del cliente ───────────────────────────────────
CREATE TABLE IF NOT EXISTS analitica.customer_features (
    customer_id       VARCHAR(100) PRIMARY KEY,
    frequency         NUMERIC(10,2),
    total_units       NUMERIC(10,2),
    unique_products   NUMERIC(10,2),
    unique_categories NUMERIC(10,2),
    avg_basket_size   NUMERIC(10,2)
);
