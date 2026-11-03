"""
Gold Star Schema Sales Fact Aggregation Module.
Modernizes jDwhVente, tHashOutput, tAggregateRow, and ODS watermark updates.
"""

from typing import Dict, Any, Optional
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col,
    count,
    sum as spark_sum,
    current_timestamp,
    lit
)

try:
    from delta.tables import DeltaTable
except ImportError:
    DeltaTable = None

from ..common.session import get_spark_session, load_config, get_table_fqn
from ..common.audit import PipelineAuditTracker


def aggregate_and_load_fact_sales(
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes Gold sales fact mart aggregation:
    1. Reads un-promoted records from silver.stg_sales (BL_LIGNE_IN_DWH = false).
    2. Performs conformed inner joins with active silver dimensions.
    3. Calculates financial measures and aggregates by dimension tuple.
    4. Inserts into gold.fact_vente.
    5. Updates watermark BL_LIGNE_IN_DWH = true in silver.stg_sales.
    """
    if config is None:
        config = load_config()

    spark = get_spark_session()
    tracker = PipelineAuditTracker("GoldFactSalesAggregator")
    tracker.start()

    sales_fqn = get_table_fqn("silver", "stg_sales", config)
    produit_fqn = get_table_fqn("silver", "dim_produit", config)
    client_fqn = get_table_fqn("silver", "dim_client", config)
    calendrier_fqn = get_table_fqn("silver", "dim_calendrier", config)
    fact_fqn = get_table_fqn("gold", "fact_vente", config)

    # 1. Query un-promoted sales records
    df_unprocessed_sales = spark.table(sales_fqn).filter(col("BL_LIGNE_IN_DWH") == False)
    unprocessed_count = df_unprocessed_sales.count()
    tracker.record_metric("Unprocessed Sales Rows", unprocessed_count)

    if unprocessed_count == 0:
        tracker.record_metric("Fact Rows Inserted", 0)
        return tracker.finish()

    # 2. Conformed active dimensions
    df_dim_produit = spark.table(produit_fqn).filter(col("BL_LIGNE_ACTIVE") == 1)
    df_dim_client = spark.table(client_fqn).filter(col("BL_LIGNE_ACTIVE") == 1)
    df_dim_calendrier = spark.table(calendrier_fqn)

    # 3. Multi-dimensional Star Join
    # Replaces tMap_1 inner joins in jDwhVente
    df_joined = (
        df_unprocessed_sales.alias("v")
        .join(
            df_dim_produit.alias("p"),
            col("v.CD_PRODUIT") == col("p.CD_PRODUIT"),
            how="inner"
        )
        .join(
            df_dim_client.alias("c"),
            col("v.ID_CLIENT") == col("c.ID_CLIENT"),
            how="inner"
        )
        .join(
            df_dim_calendrier.alias("cal"),
            col("v.DT_VENTE") == col("cal.DT_JOUR"),
            how="inner"
        )
        .select(
            col("p.ID_DIM_PRODUIT"),
            col("c.ID_DIM_CLIENT"),
            col("cal.ID_DIM_CALENDRIER"),
            col("v.ID_VENTE"),
            col("v.CD_PRODUIT"),
            col("v.QTE_VENTE"),
            (col("v.QTE_VENTE") * col("v.PRIX_ACHAT")).cast("decimal(18,2)").alias("MT_ACHAT"),
            (col("v.QTE_VENTE") * col("v.PRIX_VENTE")).cast("decimal(18,2)").alias("MT_VENTE")
        )
    )

    # Cache in memory to ensure identical records are used for aggregation & watermarking
    df_joined.cache()
    joined_count = df_joined.count()
    tracker.record_metric("Valid Joined Transactions", joined_count)

    # 4. Aggregation by Dimension Tuple
    # Replaces tAggregateRow_1 in jDwhVente
    df_fact = (
        df_joined
        .groupBy("ID_DIM_PRODUIT", "ID_DIM_CLIENT", "ID_DIM_CALENDRIER")
        .agg(
            count("ID_VENTE").alias("NB_VENTE"),
            spark_sum("QTE_VENTE").alias("NB_QTE_VENTE"),
            spark_sum("MT_ACHAT").cast("decimal(18,2)").alias("NB_MT_ACHAT"),
            spark_sum("MT_VENTE").cast("decimal(18,2)").alias("NB_MT_VENTE")
        )
        .withColumn("DT_INSERTION", current_timestamp())
        .withColumn("LB_JOB_NAME", lit("aggregate_sales_fact"))
    )

    # 5. Insert into Gold Fact Table
    df_fact.write.format("delta").mode("append").saveAsTable(fact_fqn)
    fact_count = df_fact.count()
    tracker.record_metric("Fact Rows Inserted", fact_count)

    # 6. Watermark Synchronization in silver.stg_sales
    # Replaces tMap_3 and tPostgresqlOutput in jDwhVente
    if DeltaTable is not None and DeltaTable.isDeltaTable(spark, sales_fqn):
        delta_sales = DeltaTable.forName(spark, sales_fqn)
        df_processed_keys = df_joined.select("ID_VENTE", "CD_PRODUIT").distinct()

        (
            delta_sales.alias("s")
            .merge(
                df_processed_keys.alias("p"),
                "s.ID_VENTE = p.ID_VENTE AND s.CD_PRODUIT = p.CD_PRODUIT"
            )
            .whenMatchedUpdate(set={"BL_LIGNE_IN_DWH": lit(True)})
            .execute()
        )
        tracker.record_metric("Watermark Updated in Staging", joined_count)

    df_joined.unpersist()
    return tracker.finish()


if __name__ == "__main__":
    aggregate_and_load_fact_sales()
