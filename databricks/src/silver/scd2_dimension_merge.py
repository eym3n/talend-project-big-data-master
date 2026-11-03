"""
Delta Lake SCD Type 2 Dimension Merge Engine.
Modernizes jDwhProduit and jDwhClient SCD-2 logic using native Delta Lake MERGE statements.
"""

from typing import Dict, Any, List, Optional
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col,
    current_timestamp,
    lit,
    sha2,
    concat_ws,
    coalesce
)

try:
    from delta.tables import DeltaTable
except ImportError:
    DeltaTable = None

from ..common.session import get_spark_session, load_config, get_table_fqn


def execute_scd2_merge(
    target_table_name: str,
    df_incoming: DataFrame,
    business_key_cols: List[str],
    compare_attr_cols: List[str],
    surrogate_key_col: str,
    config: Optional[Dict[str, Any]] = None
) -> None:
    """
    Executes a high-performance, idempotent SCD Type 2 MERGE onto a Delta Lake table.
    
    1. If target Delta table doesn't exist, initializes it with active records.
    2. If target exists:
       - Detects modified active records where compare_attr_cols differ.
       - Expires existing active version: is_active = 0, dt_mise_a_jour = now().
       - Inserts new version: is_active = 1, dt_insertion = now(), dt_mise_a_jour = null.
       - Inserts brand-new records: is_active = 1, dt_insertion = now().
    """
    if config is None:
        config = load_config()

    spark = get_spark_session()
    target_fqn = get_table_fqn("silver", target_table_name, config)

    # Compute deterministic surrogate hash key if identity column not present
    df_staged = df_incoming.withColumn(
        surrogate_key_col,
        sha2(concat_ws("||", *[col(c) for c in business_key_cols], current_timestamp().cast("string")), 256)
    ).withColumn("BL_LIGNE_ACTIVE", lit(1)) \
     .withColumn("DT_INSERTION", current_timestamp()) \
     .withColumn("DT_MISE_A_JOUR", lit(None).cast("timestamp")) \
     .withColumn("LB_JOB_NAME", lit(f"scd2_{target_table_name}"))

    # Table initialization if not present
    table_exists = False
    try:
        if DeltaTable is not None and DeltaTable.isDeltaTable(spark, target_fqn):
            table_exists = True
        elif spark.catalog.tableExists(target_fqn):
            table_exists = True
    except Exception:
        table_exists = False

    if not table_exists or DeltaTable is None:
        df_staged.write.format("delta").mode("overwrite").saveAsTable(target_fqn)
        return

    delta_target = DeltaTable.forName(spark, target_fqn)

    # Join condition on business keys
    key_conditions = [f"target.{k} = source.{k}" for k in business_key_cols]
    full_key_cond = " AND ".join(key_conditions)

    # Change detection condition
    diff_conditions = [f"coalesce(target.{c}, '') <> coalesce(source.{c}, '')" for c in compare_attr_cols]
    full_diff_cond = " OR ".join(diff_conditions)

    # Stage 1: Expire existing active records where attributes changed
    # Stage 2: Insert new version for changed records & brand new records
    merge_source = df_staged.alias("source")
    
    # Delta MERGE statement for SCD Type 2
    (
        delta_target.alias("target")
        .merge(
            source=merge_source,
            condition=f"({full_key_cond}) AND target.BL_LIGNE_ACTIVE = 1 AND ({full_diff_cond})"
        )
        .whenMatchedUpdate(
            set={
                "BL_LIGNE_ACTIVE": lit(0),
                "DT_MISE_A_JOUR": current_timestamp()
            }
        )
        .execute()
    )

    # Stage 2: Append new rows (brand-new keys OR new versions of expired keys)
    # Filter for rows not currently active in target with identical attributes
    df_active_target = spark.table(target_fqn).filter("BL_LIGNE_ACTIVE = 1")
    
    join_keys = business_key_cols + compare_attr_cols
    df_to_insert = df_staged.join(
        df_active_target,
        on=business_key_cols,
        how="left_anti"
    )

    if not df_to_insert.rdd.isEmpty():
        df_to_insert.write.format("delta").mode("append").saveAsTable(target_fqn)


def merge_scd2_products(
    df_clean_products: DataFrame,
    df_clean_subcategories: DataFrame,
    df_clean_categories: DataFrame,
    config: Optional[Dict[str, Any]] = None
) -> None:
    """
    Modernizes jDwhProduit:
    1. Denormalizes Product with SubCategory and Category hierarchies.
    2. Applies Delta SCD-2 merge onto silver.dim_produit.
    """
    # Denormalization join (replaces tMap_1 lookup in jDwhProduit)
    df_denorm = (
        df_clean_products.alias("p")
        .join(
            df_clean_subcategories.alias("sc"),
            col("p.CD_SOUS_CATEGORIE") == col("sc.CD_SOUS_CATEGORIE"),
            how="left"
        )
        .join(
            df_clean_categories.alias("c"),
            col("sc.CD_CATEGORIE") == col("c.CD_CATEGORIE"),
            how="left"
        )
        .select(
            col("p.CD_PRODUIT"),
            col("p.NOM_PRODUIT"),
            col("p.PRIX_ACHAT_PRODUIT").cast("decimal(18,2)").alias("PRIX_ACHAT_PRODUIT"),
            col("p.PRIX_VENTE_PRODUIT").cast("decimal(18,2)").alias("PRIX_VENTE_PRODUIT"),
            col("p.CD_SOUS_CATEGORIE"),
            coalesce(col("sc.LB_SOUS_CATEGORIE"), lit("UNKNOWN")).alias("LB_SOUS_CATEGORIE"),
            coalesce(col("sc.CD_CATEGORIE"), lit("UNKNOWN")).alias("CD_CATEGORIE"),
            coalesce(col("c.LB_CATEGORIE"), lit("UNKNOWN")).alias("LB_CATEGORIE")
        )
    )

    compare_cols = [
        "NOM_PRODUIT",
        "PRIX_ACHAT_PRODUIT",
        "PRIX_VENTE_PRODUIT",
        "CD_SOUS_CATEGORIE",
        "LB_SOUS_CATEGORIE",
        "CD_CATEGORIE",
        "LB_CATEGORIE"
    ]

    execute_scd2_merge(
        target_table_name="dim_produit",
        df_incoming=df_denorm,
        business_key_cols=["CD_PRODUIT"],
        compare_attr_cols=compare_cols,
        surrogate_key_col="ID_DIM_PRODUIT",
        config=config
    )


def merge_scd2_customers(
    df_clean_customers: DataFrame,
    df_clean_types: DataFrame,
    config: Optional[Dict[str, Any]] = None
) -> None:
    """
    Modernizes jDwhClient:
    1. Denormalizes Customer with Customer Type descriptions.
    2. Applies Delta SCD-2 merge onto silver.dim_client.
    """
    df_denorm = (
        df_clean_customers.alias("cust")
        .join(
            df_clean_types.alias("ct"),
            col("cust.CD_TYPE_CLIENT") == col("ct.CD_TYPE_CLIENT"),
            how="left"
        )
        .select(
            col("cust.ID_CLIENT"),
            col("cust.NOM_CLIENT"),
            col("cust.PREN_CLIENT"),
            col("cust.CD_POSTAL_CLIENT"),
            col("cust.VILLE_CLIENT"),
            col("cust.PAYS_CLIENT"),
            col("cust.REGION_CLIENT"),
            col("cust.CD_TYPE_CLIENT"),
            coalesce(col("ct.LB_TYPE_CLIENT"), lit("STANDARD")).alias("LB_TYPE_CLIENT")
        )
    )

    compare_cols = [
        "NOM_CLIENT",
        "PREN_CLIENT",
        "CD_POSTAL_CLIENT",
        "VILLE_CLIENT",
        "PAYS_CLIENT",
        "REGION_CLIENT",
        "CD_TYPE_CLIENT",
        "LB_TYPE_CLIENT"
    ]

    execute_scd2_merge(
        target_table_name="dim_client",
        df_incoming=df_denorm,
        business_key_cols=["ID_CLIENT"],
        compare_attr_cols=compare_cols,
        surrogate_key_col="ID_DIM_CLIENT",
        config=config
    )
