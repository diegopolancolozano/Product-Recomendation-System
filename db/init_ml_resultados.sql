-- Schema ml_resultados: salida de los modelos ML (K-Means + FP-Growth)
-- Ejecutado una sola vez al crear la instancia Cloud SQL

CREATE SCHEMA IF NOT EXISTS ml_resultados;

-- ── Clusters K-Means por cliente ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ml_resultados.customer_clusters (
    customer_id       VARCHAR(100) PRIMARY KEY,
    cluster           INTEGER,
    frequency         NUMERIC(10,2),
    total_units       NUMERIC(10,2),
    unique_products   NUMERIC(10,2),
    unique_categories NUMERIC(10,2),
    avg_basket_size   NUMERIC(10,2),
    pca1              NUMERIC(10,4),
    pca2              NUMERIC(10,4)
);

CREATE INDEX IF NOT EXISTS idx_clusters_cluster ON ml_resultados.customer_clusters(cluster);

-- ── Perfil promedio por cluster ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ml_resultados.cluster_profiles (
    cluster           INTEGER PRIMARY KEY,
    frequency         NUMERIC(10,2),
    total_units       NUMERIC(10,2),
    unique_products   NUMERIC(10,2),
    unique_categories NUMERIC(10,2),
    avg_basket_size   NUMERIC(10,2),
    size              INTEGER
);

-- ── Reglas de asociacion (FP-Growth) ─────────────────────────────────────────
-- antecedent y consequent son product_id
CREATE TABLE IF NOT EXISTS ml_resultados.association_rules (
    id          BIGSERIAL PRIMARY KEY,
    antecedent  BIGINT,
    consequent  BIGINT,
    support     NUMERIC(10,6),
    confidence  NUMERIC(10,6),
    lift        NUMERIC(10,4)
);

CREATE INDEX IF NOT EXISTS idx_rules_antecedent ON ml_resultados.association_rules(antecedent);
CREATE INDEX IF NOT EXISTS idx_rules_consequent ON ml_resultados.association_rules(consequent);

-- ── Metadatos de la ultima ejecucion ML ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS ml_resultados.run_metadata (
    id           BIGSERIAL PRIMARY KEY,
    run_at       TIMESTAMP DEFAULT NOW(),
    n_clusters   INTEGER,
    n_rules      BIGINT,
    min_support  NUMERIC(10,4),
    min_confidence NUMERIC(10,4)
);
