"""
Bronze Raw Ingestion Module for Ingress Delimited Feeds.
Modernizes tFileList_1, tFileInputDelimited_1, and raw staging into Delta Bronze tables.
"""

import os
import glob
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    input_file_name,
    current_timestamp,
    lit
)

from ..common.session import get_spark_session, load_config, get_table_fqn
from ..common.audit import PipelineAuditTracker


def validate_ingress_directory(base_path: str, execution_date: Optional[str] = None) -> str:
    """
    Equivalence of tFileList_1 + tDie_1 in jChargeODS:
    Verifies that the target execution date directory exists.
    Raises FileNotFoundError with code 4 context if missing.
    """
    if execution_date is None:
        execution_date = datetime.now().strftime("%Y%m%d")

    target_dir = os.path.join(base_path, execution_date)
    # Check if target directory exists; fallback to base_path if flat structure used in dev/poc
    if not os.path.exists(target_dir):
        if os.path.exists(base_path):
            # If date subfolder missing but flat files exist in base_path, allow fallback in non-prod
            return base_path
        raise FileNotFoundError(
            f"Exit Code 4: Le repertoire du jour '{execution_date}' n'existe pas dans '{base_path}'. "
            "Veuillez deposer les fichiers du jour et relancer l'integration."
        )
    return target_dir


def ingest_feed(
    feed_name: str,
    source_dir: str,
    config: Optional[Dict[str, Any]] = None,
    execution_date: Optional[str] = None
) -> DataFrame:
    """
    Reads a single delimited feed and writes it to its designated Bronze Delta table.
    """
    if config is None:
        config = load_config()

    spark = get_spark_session()
    feed_cfg = config["feeds"][feed_name]
    delimiter = config["file_formats"]["delimiter"]
    encoding = config["file_formats"]["encoding"]
    pattern = feed_cfg["pattern"]
    target_table = get_table_fqn("bronze", feed_cfg["bronze_table"], config)

    search_path = os.path.join(source_dir, pattern)
    matching_files = glob.glob(search_path)
    if not matching_files:
        raise FileNotFoundError(f"Aucun fichier correspondant a '{pattern}' dans '{source_dir}'")

    if execution_date is None:
        execution_date = datetime.now().strftime("%Y%m%d")

    # Read CSV with schema-on-read and explicit delimiter
    df_raw = (
        spark.read
        .option("header", "true")
        .option("delimiter", delimiter)
        .option("encoding", encoding)
        .option("inferSchema", "false")  # Preserve raw strings for Silver type casting/validation
        .csv(search_path)
    )

    # Attach lineage and audit metadata
    df_enriched = (
        df_raw
        .withColumn("_ingest_file_name", input_file_name())
        .withColumn("_ingest_timestamp", current_timestamp())
        .withColumn("_ingest_date", lit(execution_date))
        .withColumn("_feed_name", lit(feed_name))
    )

    # Write to Bronze Delta Table (Append mode)
    df_enriched.write.format("delta").mode("append").saveAsTable(target_table)
    return df_enriched


def ingest_all_feeds(
    source_dir: Optional[str] = None,
    config_path: Optional[str] = None,
    execution_date: Optional[str] = None
) -> Dict[str, int]:
    """
    Orchestrates Bronze ingestion for all 6 business feeds in order.
    """
    config = load_config(config_path)
    tracker = PipelineAuditTracker("BronzeIngestionPipeline")
    tracker.start()

    if source_dir is None:
        source_dir = config["storage"].get("local_fallback_path", "csvFiles")

    validated_dir = validate_ingress_directory(source_dir, execution_date)
    results = {}

    feed_order = ["category", "subcategory", "product", "customer_type", "customer", "sales"]
    for feed in feed_order:
        df = ingest_feed(feed, validated_dir, config, execution_date)
        count = df.count()
        results[feed] = count
        tracker.record_metric(f"Bronze Ingested: {feed}", count)

    tracker.finish()
    return results


if __name__ == "__main__":
    ingest_all_feeds()
