"""
End-to-End Modernized Pipeline Execution Harness.
Replaces jAlimentationBDD, coordinating Bronze, Silver, and Gold execution stages.
"""

import sys
from typing import Optional

from .common.session import load_config, get_spark_session
from .common.audit import PipelineAuditTracker
from .bronze.ingest_raw_feeds import ingest_all_feeds
from .silver.clean_reference_data import clean_and_quarantine_feed
from .silver.scd2_dimension_merge import merge_scd2_products, merge_scd2_customers
from .silver.build_calendar_dimension import build_calendar_dimension
from .silver.clean_sales_transactions import clean_sales_transactions
from .gold.aggregate_sales_fact import aggregate_and_load_fact_sales


def run_full_pipeline(
    source_dir: Optional[str] = None,
    execution_date: Optional[str] = None,
    config_path: Optional[str] = None
) -> None:
    """
    Executes the entire modernized lakehouse pipeline:
    1. Bronze Ingestion
    2. Silver Reference Cleaning and SCD-2 Merges
    3. Silver Calendar Generation
    4. Silver Sales Staging & Quarantine
    5. Gold Fact Sales Mart Aggregation
    """
    config = load_config(config_path)
    spark = get_spark_session()
    master_tracker = PipelineAuditTracker("MasterLakehousePipeline")
    master_tracker.start()

    # Stage 1: Bronze Ingestion (replaces jChargeODS file ingress)
    print("\n>>> Stage 1: Ingesting Raw Feeds into Bronze Delta Lake...")
    bronze_results = ingest_all_feeds(source_dir, config_path, execution_date)

    # Stage 2: Silver Reference Cleansing & SCD-2 Merges
    print("\n>>> Stage 2: Cleansing Reference Data & Applying SCD-2 Merges...")
    df_raw_cat = spark.table(f"{config['catalog']}.{config['schemas']['bronze']}.raw_categories")
    df_raw_scat = spark.table(f"{config['catalog']}.{config['schemas']['bronze']}.raw_subcategories")
    df_raw_prod = spark.table(f"{config['catalog']}.{config['schemas']['bronze']}.raw_products")
    df_raw_types = spark.table(f"{config['catalog']}.{config['schemas']['bronze']}.raw_customer_types")
    df_raw_cust = spark.table(f"{config['catalog']}.{config['schemas']['bronze']}.raw_customers")

    df_clean_cat, _ = clean_and_quarantine_feed("category", df_raw_cat, config)
    df_clean_scat, _ = clean_and_quarantine_feed("subcategory", df_raw_scat, config)
    df_clean_prod, _ = clean_and_quarantine_feed("product", df_raw_prod, config)
    df_clean_types, _ = clean_and_quarantine_feed("customer_type", df_raw_types, config)
    df_clean_cust, _ = clean_and_quarantine_feed("customer", df_raw_cust, config)

    merge_scd2_products(df_clean_prod, df_clean_scat, df_clean_cat, config)
    merge_scd2_customers(df_clean_cust, df_clean_types, config)

    # Stage 3: Calendar Generation (replaces jGenerateCalendar)
    print("\n>>> Stage 3: Building Calendar Dimension...")
    build_calendar_dimension(
        start_date=config["calendar"]["start_date"],
        end_date=config["calendar"]["end_date"],
        config=config
    )

    # Stage 4: Silver Sales Staging (replaces jOdsVente)
    print("\n>>> Stage 4: Validating Sales Transactions & Staging...")
    clean_sales_transactions(config=config)

    # Stage 5: Gold Fact Aggregation (replaces jDwhVente)
    print("\n>>> Stage 5: Aggregating Gold Sales Mart...")
    fact_results = aggregate_and_load_fact_sales(config=config)

    master_tracker.record_metric("Pipeline Status", "SUCCESS")
    master_tracker.finish()


if __name__ == "__main__":
    src_dir = sys.argv[1] if len(sys.argv) > 1 else None
    exec_dt = sys.argv[2] if len(sys.argv) > 2 else None
    run_full_pipeline(source_dir=src_dir, execution_date=exec_dt)
