"""
Job 1 — ETL (Extract, Transform, Load)
Dataproc Worker Node — Pipeline Spark

Lee los CSV de transacciones y catalogo desde Cloud Storage (/raw),
normaliza los datos y los escribe en Cloud SQL (schema staging).

Ejecucion:
    spark-submit 01_etl.py \
        --bucket=<BUCKET> \
        --db_host=<CLOUD_SQL_IP> \
        --db_user=supermarket \
        --db_password=<PASSWORD>
"""
from __future__ import annotations

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    LongType, StringType, StructField, StructType,
)


# ── Schemas de entrada ────────────────────────────────────────────────────────

TRANSACTION_SCHEMA = StructType([
    StructField("date",         StringType(), True),
    StructField("store_id",     StringType(), True),
    StructField("customer_id",  StringType(), True),
    StructField("product_list", StringType(), True),
])

CATEGORY_SCHEMA = StructType([
    StructField("category_id",   LongType(),   True),
    StructField("category_name", StringType(), True),
])


def main(args: argparse.Namespace) -> None:
    spark = (
        SparkSession.builder
        .appName("SupermarketETL")
        .config("spark.jars", "gs://spark-lib/bigquery/spark-bigquery-latest_2.12.jar")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    db_url   = f"jdbc:postgresql://{args.db_host}:5432/analitica"
    db_props = {
        "user":     args.db_user,
        "password": args.db_password,
        "driver":   "org.postgresql.Driver",
    }

    bucket = args.bucket

    # ── 1. Leer transacciones ─────────────────────────────────────────────────
    print("[ETL 1/5] Leyendo transacciones desde GCS...")
    trans_raw = (
        spark.read
        .option("sep", "|")
        .schema(TRANSACTION_SCHEMA)
        .csv(f"gs://{bucket}/raw/Transactions/*.csv")
    )

    # Limpiar y normalizar
    trans = (
        trans_raw
        .filter(F.col("customer_id").isNotNull())
        .filter(F.col("product_list").isNotNull())
        .withColumn("date", F.to_date(F.col("date"), "yyyy-MM-dd"))
        .filter(F.col("date").isNotNull())
        .withColumn(
            "transaction_uid",
            F.concat(F.col("store_id"), F.lit("-"), F.monotonically_increasing_id().cast("string"))
        )
    )
    print(f"    {trans.count():,} transacciones validas")

    # ── 2. Explotar items ─────────────────────────────────────────────────────
    print("[ETL 2/5] Explotando items por producto...")
    items_raw = (
        trans
        .withColumn("product_id_str", F.explode(F.split(F.col("product_list"), " ")))
        .filter(F.col("product_id_str") != "")
        .withColumn("product_id", F.col("product_id_str").cast(LongType()))
        .filter(F.col("product_id").isNotNull())
        .drop("product_id_str", "product_list")
    )

    # ── 3. Leer catalogo de productos ─────────────────────────────────────────
    print("[ETL 3/5] Leyendo catalogo de productos...")
    categories = (
        spark.read
        .option("sep", "|")
        .schema(CATEGORY_SCHEMA)
        .csv(f"gs://{bucket}/raw/Products/Categories.csv")
    )

    product_cat = (
        spark.read
        .option("sep", "|")
        .option("header", "true")
        .csv(f"gs://{bucket}/raw/Products/ProductCategory.csv")
        .withColumnRenamed("v.Code_pr", "product_id")
        .withColumnRenamed("v.code",    "category_id")
        .withColumn("product_id",  F.col("product_id").cast(LongType()))
        .withColumn("category_id", F.col("category_id").cast(LongType()))
        .dropna(subset=["product_id", "category_id"])
    )

    # ── 4. Join items con catalogo ────────────────────────────────────────────
    print("[ETL 4/5] Enriqueciendo items con categorias...")
    items = (
        items_raw
        .join(product_cat, "product_id", "left")
        .join(categories,  "category_id", "left")
        .fillna({"category_name": "Sin categoria"})
    )
    print(f"    {items.count():,} items con categoria asignada")

    # ── 5. Escribir en Cloud SQL ──────────────────────────────────────────────
    print("[ETL 5/5] Escribiendo en Cloud SQL (staging)...")

    (
        trans
        .select("transaction_uid", "date", "store_id", "customer_id", "product_list")
        .write
        .jdbc(url=db_url, table="staging.transactions", mode="overwrite", properties=db_props)
    )

    (
        items
        .select("transaction_uid", "date", "store_id", "customer_id",
                "product_id", "category_id", "category_name")
        .write
        .jdbc(url=db_url, table="staging.items", mode="overwrite", properties=db_props)
    )

    print("ETL completado exitosamente.")
    spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supermarket ETL — PySpark")
    parser.add_argument("--bucket",      required=True,  help="Nombre del bucket GCS")
    parser.add_argument("--db_host",     required=True,  help="IP publica de Cloud SQL")
    parser.add_argument("--db_user",     default="supermarket")
    parser.add_argument("--db_password", required=True)
    main(parser.parse_args())
