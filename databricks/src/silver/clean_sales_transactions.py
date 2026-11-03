"""
Silver Sales Transactions Cleaning and Staging Module.
Modernizes jOdsVente validation, deduplication, quarantine, and watermark initialization.
"""

from typing import Dict, Any, Optional
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col,
    to_date,
    lit,
    current_timestamp
)
from pyspark.sql.types import (
    IntegerType,
    DecimalType
)

from ..common.session import get_spark_session, load_config, get_table_fqn
from .clean_reference_data import clean_and_quarantine_feed


def clean_sales_transactions(
    df_bronze_sales: Optional[DataFrame] = None,
    config: Optional[Dict[str, Any]] = None
) -> DataFrame:
    """
    Cleans Bronze raw sales transactions:
    - Filters null/empty mandatory fields to quarantine.
    - Filters duplicates on (ID_VENTE, CD_PRODUIT) to quarantine.
    - Formats types and initializes BL_LIGNE_IN_DWH = false.
    - Writes clean staged transactions to silver.stg_sales.
    """
    if config is None:
        config = load_config()

    spark = get_spark_session()
    if df_bronze_sales is None:
        raw_table = get_table_fqn("bronze", "raw_sales", config)
        df_bronze_sales = spark.table(raw_table)

    df_clean, df_quarantine = clean_and_quarantine_feed("sales", df_bronze_sales, config)

    # Cast data types to strict target contracts
    df_staged_sales = (
        df_clean
        .withColumn("ID_VENTE", col("ID_VENTE"))
        .withColumn("CD_PRODUIT", col("CD_PRODUIT"))
        .withColumn("DT_VENTE", to_date(col("DT_VENTE"), "dd-MM-yyyy"))
        .withColumn("ID_CLIENT", col("ID_CLIENT"))
        .withColumn("QTE_VENTE", col("QTE_VENTE").cast(IntegerType()))
        .withColumn("PRIX_ACHAT", col("PRIX_ACHAT").cast(DecimalType(18, 2)))
        .withColumn("PRIX_VENTE", col("PRIX_VENTE").cast(DecimalType(18, 2)))
        .withColumn("LB_NOM_FICHIER", col("_ingest_file_name"))
        .withColumn("DT_INSERTION", current_timestamp())
        .withColumn("LB_JOB_NAME", lit("clean_sales_transactions"))
        .withColumn("BL_LIGNE_IN_DWH", lit(False))
        .select(
            "ID_VENTE",
            "CD_PRODUIT",
            "DT_VENTE",
            "ID_CLIENT",
            "QTE_VENTE",
            "PRIX_ACHAT",
            "PRIX_VENTE",
            "LB_NOM_FICHIER",
            "DT_INSERTION",
            "LB_JOB_NAME",
            "BL_LIGNE_IN_DWH"
        )
    )

    target_fqn = get_table_fqn("silver", "stg_sales", config)
    df_staged_sales.write.format("delta").mode("append").saveAsTable(target_fqn)
    return df_staged_sales
