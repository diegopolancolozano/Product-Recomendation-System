"""
Job 2 — Machine Learning (K-Means + FP-Growth)
Dataproc Worker Node — Pipeline Spark MLlib

Lee los datos normalizados de staging, aplica:
  - K-Means (k=4) sobre features de comportamiento del cliente
  - FP-Growth para reglas de asociacion entre productos

Escribe los resultados en Cloud SQL (schema ml_resultados).

Ejecucion:
    spark-submit 02_ml.py \
        --db_host=<CLOUD_SQL_IP> \
        --db_user=supermarket \
        --db_password=<PASSWORD> \
        [--n_clusters=4] \
        [--min_support=0.01] \
        [--min_confidence=0.1]
"""
from __future__ import annotations

import argparse

from pyspark.ml.clustering import KMeans
from pyspark.ml.feature import StandardScaler, VectorAssembler
from pyspark.ml.fpm import FPGrowth
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml.feature import PCA as SparkPCA


FEATURE_COLS = [
    "frequency",
    "total_units",
    "unique_products",
    "unique_categories",
    "avg_basket_size",
]


def main(args: argparse.Namespace) -> None:
    spark = SparkSession.builder.appName("SupermarketML").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    db_url   = f"jdbc:postgresql://{args.db_host}:5432/analitica"
    ml_url   = f"jdbc:postgresql://{args.db_host}:5432/ml_resultados"
    db_props = {
        "user":     args.db_user,
        "password": args.db_password,
        "driver":   "org.postgresql.Driver",
    }

    # ── 1. Construir features por cliente ─────────────────────────────────────
    print("[ML 1/6] Leyendo staging.items desde Cloud SQL...")
    items = (
        spark.read
        .jdbc(url=db_url, table="staging.items", properties=db_props)
        .cache()
    )

    trans = (
        spark.read
        .jdbc(url=db_url, table="staging.transactions", properties=db_props)
        .cache()
    )

    print("[ML 2/6] Calculando features por cliente...")
    frequency = (
        trans.groupBy("customer_id")
        .agg(F.countDistinct("transaction_uid").alias("frequency"))
    )
    total_units = (
        items.groupBy("customer_id")
        .agg(F.count("product_id").alias("total_units"))
    )
    unique_products = (
        items.groupBy("customer_id")
        .agg(F.countDistinct("product_id").alias("unique_products"))
    )
    unique_categories = (
        items.groupBy("customer_id")
        .agg(F.countDistinct("category_id").alias("unique_categories"))
    )

    features = (
        frequency
        .join(total_units,      "customer_id", "left")
        .join(unique_products,  "customer_id", "left")
        .join(unique_categories,"customer_id", "left")
        .fillna(0)
        .withColumn(
            "avg_basket_size",
            F.when(F.col("frequency") > 0, F.col("total_units") / F.col("frequency"))
             .otherwise(0.0)
        )
    )

    # ── 2. K-Means ────────────────────────────────────────────────────────────
    print(f"[ML 3/6] Ejecutando K-Means (k={args.n_clusters})...")
    assembler = VectorAssembler(inputCols=FEATURE_COLS, outputCol="features_raw")
    scaler    = StandardScaler(inputCol="features_raw", outputCol="features_scaled",
                               withMean=True, withStd=True)
    kmeans    = KMeans(featuresCol="features_scaled", predictionCol="cluster",
                       k=args.n_clusters, seed=42, maxIter=20)

    # Pipeline manual (sin Pipeline de ML para simplicidad)
    assembled = assembler.transform(features)
    scaler_model  = scaler.fit(assembled)
    scaled        = scaler_model.transform(assembled)
    kmeans_model  = kmeans.fit(scaled)
    clustered     = kmeans_model.transform(scaled)

    # PCA 2D para visualizacion
    pca_model = SparkPCA(k=2, inputCol="features_scaled", outputCol="pca_coords").fit(scaled)
    clustered = pca_model.transform(clustered)
    clustered = (
        clustered
        .withColumn("pca1", F.col("pca_coords")[0])
        .withColumn("pca2", F.col("pca_coords")[1])
    )

    # ── 3. Guardar clusters en Cloud SQL ──────────────────────────────────────
    print("[ML 4/6] Escribiendo clusters en ml_resultados...")
    (
        clustered
        .select("customer_id", "cluster", *FEATURE_COLS, "pca1", "pca2")
        .write
        .jdbc(url=ml_url, table="ml_resultados.customer_clusters",
              mode="overwrite", properties=db_props)
    )

    # Perfil promedio por cluster
    profiles = (
        clustered
        .groupBy("cluster")
        .agg(
            F.round(F.avg("frequency"),         2).alias("frequency"),
            F.round(F.avg("total_units"),       2).alias("total_units"),
            F.round(F.avg("unique_products"),   2).alias("unique_products"),
            F.round(F.avg("unique_categories"), 2).alias("unique_categories"),
            F.round(F.avg("avg_basket_size"),   2).alias("avg_basket_size"),
            F.count("customer_id").alias("size"),
        )
        .orderBy("cluster")
    )
    profiles.write.jdbc(url=ml_url, table="ml_resultados.cluster_profiles",
                        mode="overwrite", properties=db_props)

    # ── 4. FP-Growth — reglas de asociacion ───────────────────────────────────
    print("[ML 5/6] Ejecutando FP-Growth...")
    baskets = (
        items
        .groupBy("transaction_uid")
        .agg(F.collect_set("product_id").alias("items"))
        .filter(F.size("items") >= 2)
    )

    fpgrowth = FPGrowth(
        itemsCol="items",
        minSupport=args.min_support,
        minConfidence=args.min_confidence,
    )
    fp_model = fpgrowth.fit(baskets)
    rules    = fp_model.associationRules

    # Filtrar solo reglas de un antecedente → un consecuente
    rules_filtered = (
        rules
        .filter(F.size("antecedent") == 1)
        .filter(F.size("consequent") == 1)
        .withColumn("antecedent", F.col("antecedent")[0].cast("long"))
        .withColumn("consequent", F.col("consequent")[0].cast("long"))
        .select("antecedent", "consequent", "support", "confidence", "lift")
    )

    print("[ML 6/6] Escribiendo reglas de asociacion en ml_resultados...")
    rules_filtered.write.jdbc(
        url=ml_url, table="ml_resultados.association_rules",
        mode="overwrite", properties=db_props
    )

    n_rules = rules_filtered.count()

    # Metadatos de la ejecucion
    spark.createDataFrame([{
        "n_clusters":      args.n_clusters,
        "n_rules":         n_rules,
        "min_support":     args.min_support,
        "min_confidence":  args.min_confidence,
    }]).write.jdbc(url=ml_url, table="ml_resultados.run_metadata",
                   mode="append", properties=db_props)

    print(f"ML completado: {args.n_clusters} clusters, {n_rules:,} reglas de asociacion.")
    spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supermarket ML — PySpark MLlib")
    parser.add_argument("--db_host",        required=True)
    parser.add_argument("--db_user",        default="supermarket")
    parser.add_argument("--db_password",    required=True)
    parser.add_argument("--n_clusters",     type=int,   default=4)
    parser.add_argument("--min_support",    type=float, default=0.01)
    parser.add_argument("--min_confidence", type=float, default=0.1)
    main(parser.parse_args())
