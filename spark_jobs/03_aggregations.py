"""
Job 3 — Aggregations (KPIs + Patrones)
Dataproc Worker Node — Pipeline Spark

Lee staging.items y staging.transactions, calcula todos los KPIs
y patrones temporales, y los escribe en Cloud SQL (schema analitica).

Ejecucion:
    spark-submit 03_aggregations.py \
        --db_host=<CLOUD_SQL_IP> \
        --db_user=supermarket \
        --db_password=<PASSWORD>
"""
from __future__ import annotations

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import LongType


WEEKDAY_NAMES = {0: "Lunes", 1: "Martes", 2: "Miercoles",
                 3: "Jueves", 4: "Viernes", 5: "Sabado", 6: "Domingo"}


def main(args: argparse.Namespace) -> None:
    spark = SparkSession.builder.appName("SupermarketAggregations").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    db_url   = f"jdbc:postgresql://{args.db_host}:5432/analitica"
    db_props = {
        "user":     args.db_user,
        "password": args.db_password,
        "driver":   "org.postgresql.Driver",
    }

    print("[AGG 1/8] Leyendo datos de staging...")
    items = spark.read.jdbc(url=db_url, table="staging.items",        properties=db_props).cache()
    trans = spark.read.jdbc(url=db_url, table="staging.transactions",  properties=db_props).cache()

    # ── KPIs globales ─────────────────────────────────────────────────────────
    print("[AGG 2/8] KPIs globales...")
    total_units        = items.count()
    total_transactions = trans.select("transaction_uid").distinct().count()

    spark.createDataFrame([{
        "total_units":        total_units,
        "total_transactions": total_transactions,
    }]).write.jdbc(url=db_url, table="analitica.kpis", mode="overwrite", properties=db_props)

    # ── Top 10 productos ──────────────────────────────────────────────────────
    print("[AGG 3/8] Top productos...")
    top_products = (
        items
        .groupBy("product_id", "category_name")
        .agg(F.count("transaction_uid").alias("units"))
        .orderBy(F.desc("units"))
        .limit(10)
        .withColumn("rank", F.monotonically_increasing_id().cast(LongType()) + 1)
        .select("rank", "product_id", "category_name", "units")
    )
    top_products.write.jdbc(url=db_url, table="analitica.top_products",
                            mode="overwrite", properties=db_props)

    # ── Top 10 clientes ───────────────────────────────────────────────────────
    print("[AGG 4/8] Top clientes...")
    top_customers = (
        trans
        .groupBy("customer_id")
        .agg(F.countDistinct("transaction_uid").alias("transactions"))
        .orderBy(F.desc("transactions"))
        .limit(10)
        .withColumn("rank", F.monotonically_increasing_id().cast(LongType()) + 1)
        .select("rank", "customer_id", "transactions")
    )
    top_customers.write.jdbc(url=db_url, table="analitica.top_customers",
                             mode="overwrite", properties=db_props)

    # ── Series de tiempo diarias ──────────────────────────────────────────────
    print("[AGG 5/8] Series de tiempo...")
    units_per_day = (
        items.filter(F.col("date").isNotNull())
        .groupBy("date")
        .agg(F.count("product_id").alias("units"))
        .orderBy("date")
    )
    units_per_day.write.jdbc(url=db_url, table="analitica.units_per_day",
                             mode="overwrite", properties=db_props)

    transactions_per_day = (
        trans.filter(F.col("date").isNotNull())
        .groupBy("date")
        .agg(F.countDistinct("transaction_uid").alias("transactions"))
        .orderBy("date")
    )
    transactions_per_day.write.jdbc(url=db_url, table="analitica.transactions_per_day",
                                    mode="overwrite", properties=db_props)

    # ── Categorias ────────────────────────────────────────────────────────────
    print("[AGG 6/8] Unidades por categoria...")
    category_units = (
        items
        .groupBy("category_name")
        .agg(F.count("product_id").alias("units"))
        .orderBy(F.desc("units"))
        .limit(10)
        .withColumn("rank", F.monotonically_increasing_id().cast(LongType()) + 1)
    )
    category_units.write.jdbc(url=db_url, table="analitica.category_units",
                              mode="overwrite", properties=db_props)

    # ── Unidades por cliente (para boxplot) ───────────────────────────────────
    customer_units = (
        items.groupBy("customer_id")
        .agg(F.count("product_id").alias("total_units"))
    )
    customer_units.write.jdbc(url=db_url, table="analitica.customer_units",
                              mode="overwrite", properties=db_props)

    # ── Patrones temporales ───────────────────────────────────────────────────
    print("[AGG 7/8] Patrones por dia de semana y tienda...")

    # Dia de la semana (0=Lunes ... 6=Domingo)
    trans_wd = trans.filter(F.col("date").isNotNull()) \
                    .withColumn("weekday", F.dayofweek(F.col("date")) - 2)  # ajuste a lunes=0
    trans_wd = trans_wd.withColumn(
        "weekday", F.when(F.col("weekday") < 0, 6).otherwise(F.col("weekday"))
    )
    trans_wd = trans_wd.withColumn("date_only", F.col("date").cast("date"))

    days_per_wd = (
        trans_wd.select("weekday", "date_only").distinct()
        .groupBy("weekday").agg(F.count("date_only").alias("num_days"))
    )
    txn_per_wd = (
        trans_wd.groupBy("weekday")
        .agg(F.countDistinct("transaction_uid").alias("total_transactions"))
    )

    items_wd = items.filter(F.col("date").isNotNull()) \
                    .withColumn("weekday", F.dayofweek(F.col("date")) - 2)
    items_wd = items_wd.withColumn(
        "weekday", F.when(F.col("weekday") < 0, 6).otherwise(F.col("weekday"))
    )
    units_wd = items_wd.groupBy("weekday").agg(F.count("product_id").alias("total_units"))

    weekday_map = spark.createDataFrame(
        [(k, v) for k, v in WEEKDAY_NAMES.items()], ["weekday", "day_name"]
    )
    weekday_patterns = (
        txn_per_wd
        .join(days_per_wd, "weekday", "left")
        .join(units_wd, "weekday", "left")
        .join(weekday_map, "weekday", "left")
        .withColumn("avg_transactions",
                    F.round(F.col("total_transactions") / F.col("num_days"), 1))
        .withColumn("avg_units",
                    F.round(F.col("total_units") / F.col("num_days"), 1))
        .select("weekday", "day_name", "total_transactions", "avg_transactions", "avg_units")
        .orderBy("weekday")
    )
    weekday_patterns.write.jdbc(url=db_url, table="analitica.weekday_patterns",
                                mode="overwrite", properties=db_props)

    # Patrones por tienda
    store_patterns = (
        trans.groupBy("store_id")
        .agg(F.countDistinct("transaction_uid").alias("transactions"))
        .join(
            items.groupBy("store_id").agg(F.count("product_id").alias("units")),
            "store_id", "left"
        )
        .orderBy(F.desc("transactions"))
    )
    store_patterns.write.jdbc(url=db_url, table="analitica.store_patterns",
                              mode="overwrite", properties=db_props)

    # ── Features por cliente (para correlacion) ───────────────────────────────
    print("[AGG 8/8] Features por cliente...")
    frequency = (
        trans.groupBy("customer_id")
        .agg(F.countDistinct("transaction_uid").alias("frequency"))
    )
    total_units_cust = (
        items.groupBy("customer_id")
        .agg(F.count("product_id").alias("total_units"))
    )
    unique_prod = (
        items.groupBy("customer_id")
        .agg(F.countDistinct("product_id").alias("unique_products"))
    )
    unique_cat = (
        items.groupBy("customer_id")
        .agg(F.countDistinct("category_id").alias("unique_categories"))
    )

    customer_features = (
        frequency
        .join(total_units_cust, "customer_id", "left")
        .join(unique_prod,      "customer_id", "left")
        .join(unique_cat,       "customer_id", "left")
        .fillna(0)
        .withColumn(
            "avg_basket_size",
            F.round(
                F.when(F.col("frequency") > 0,
                       F.col("total_units") / F.col("frequency"))
                 .otherwise(0.0),
                2
            )
        )
    )
    customer_features.write.jdbc(url=db_url, table="analitica.customer_features",
                                 mode="overwrite", properties=db_props)

    # ── Histograma de frecuencia ──────────────────────────────────────────────
    bucket_udf = F.udf(lambda n: (
        str(n) if n <= 5
        else "6-10" if n <= 10
        else "11-20" if n <= 20
        else "21+"
    ))
    freq_hist = (
        frequency
        .withColumn("bucket", bucket_udf(F.col("frequency")))
        .groupBy("bucket").agg(F.count("customer_id").alias("customers"))
    )
    freq_hist.write.jdbc(url=db_url, table="analitica.freq_histogram",
                         mode="overwrite", properties=db_props)

    print("Agregaciones completadas exitosamente.")
    spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supermarket Aggregations — PySpark")
    parser.add_argument("--db_host",     required=True)
    parser.add_argument("--db_user",     default="supermarket")
    parser.add_argument("--db_password", required=True)
    main(parser.parse_args())
