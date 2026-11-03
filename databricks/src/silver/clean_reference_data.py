"""
Silver Data Quality and Quarantine Cleansing Module.
Modernizes tFilterRow (null checks), tUniqRow (duplicate checks), and tMap_3/4 (ODS_REJET).
"""

from typing import Dict, Any, List, Optional, Tuple
from pyspark.sql import DataFrame, Window
from pyspark.sql.functions import (
    col,
    concat_ws,
    current_timestamp,
    lit,
    row_number,
    when
)

from ..common.session import get_spark_session, load_config, load_quality_rules, get_table_fqn


def clean_and_quarantine_feed(
    feed_name: str,
    df_bronze: DataFrame,
    config: Optional[Dict[str, Any]] = None,
    quality_rules: Optional[Dict[str, Any]] = None
) -> Tuple[DataFrame, DataFrame]:
    """
    Applies BR-VAL-* and BR-DEDUP-* rules to incoming Bronze DataFrame.
    Returns (df_clean, df_rejects).
    """
    if config is None:
        config = load_config()
    if quality_rules is None:
        quality_rules = load_quality_rules()

    feed_cfg = config["feeds"][feed_name]
    mandatory_fields = quality_rules["rules"][feed_name]["mandatory_fields"]
    business_keys = feed_cfg["business_keys"]
    msg_nulls = quality_rules["rejection_messages"]["null_values"]
    msg_duplicates = quality_rules["rejection_messages"]["duplicate_data"]

    # 1. Evaluate Null Condition (BR-VAL)
    # A row is invalid if ANY mandatory field is null or empty
    null_condition = None
    for field in mandatory_fields:
        field_invalid = col(field).isNull() | (col(field) == "")
        null_condition = field_invalid if null_condition is None else (null_condition | field_invalid)

    df_null_rejects = (
        df_bronze.filter(null_condition)
        .withColumn("LB_MESSAGE_REJET", lit(msg_nulls))
        .withColumn("LB_NOM_FLUX", lit(feed_name.upper()))
        .withColumn("DT_REJET", current_timestamp())
    )

    df_non_null = df_bronze.filter(~null_condition)

    # 2. Evaluate Duplicate Condition (BR-DEDUP)
    # Deduplicate on business keys using row_number window
    window_spec = Window.partitionBy([col(k) for k in business_keys]).orderBy(col("_ingest_timestamp"))
    df_windowed = df_non_null.withColumn("_row_num", row_number().over(window_spec))

    df_clean = df_windowed.filter(col("_row_num") == 1).drop("_row_num")

    df_duplicate_rejects = (
        df_windowed.filter(col("_row_num") > 1)
        .drop("_row_num")
        .withColumn("LB_MESSAGE_REJET", lit(msg_duplicates))
        .withColumn("LB_NOM_FLUX", lit(feed_name.upper()))
        .withColumn("DT_REJET", current_timestamp())
    )

    # Combine all rejects for the quarantine table
    payload_cols = [c for c in df_bronze.columns if not c.startswith("_")]
    
    def format_rejects(df_rej: DataFrame) -> DataFrame:
        if df_rej.rdd.isEmpty():
            return df_rej
        return (
            df_rej
            .withColumn("LB_CHEMIN_FICHIER", col("_ingest_file_name"))
            .withColumn("LB_NOM_FICHIER", col("_ingest_file_name"))
            .withColumn("NUM_LIGNE_REJET", lit(0))  # Preserved for contract schema parity
            .withColumn("LB_LIGNE_REJET", concat_ws("|", *[col(c) for c in payload_cols]))
            .withColumn("LB_JOB_NAME", lit(f"clean_{feed_name}"))
            .select(
                "LB_CHEMIN_FICHIER",
                "LB_NOM_FICHIER",
                "NUM_LIGNE_REJET",
                "LB_LIGNE_REJET",
                "LB_MESSAGE_REJET",
                "LB_NOM_FLUX",
                "DT_REJET",
                "LB_JOB_NAME"
            )
        )

    df_all_rejects = df_null_rejects.unionByName(df_duplicate_rejects, allowMissingColumns=True)
    df_quarantine = format_rejects(df_all_rejects)

    # Persist quarantine records to Silver Quarantine Delta Table if any exist
    if not df_quarantine.rdd.isEmpty():
        quarantine_table = get_table_fqn("silver", "silver_quarantine_rejets", config)
        df_quarantine.write.format("delta").mode("append").saveAsTable(quarantine_table)

    return df_clean, df_quarantine
