"""
SparkSession and Configuration Management for Databricks Lakehouse Pipeline.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from pyspark.sql import SparkSession
except ImportError:
    SparkSession = None  # Handled gracefully for offline unit testing


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads pipeline configuration YAML.
    """
    if not config_path:
        # Default to ../../config/pipeline_config.yaml relative to this file
        current_dir = Path(__file__).resolve().parent
        config_path = current_dir.parent.parent / "config" / "pipeline_config.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def load_quality_rules(rules_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads quality rules YAML.
    """
    if not rules_path:
        current_dir = Path(__file__).resolve().parent
        rules_path = current_dir.parent.parent / "config" / "quality_rules.yaml"

    with open(rules_path, "r", encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    return rules


def get_spark_session(app_name: str = "TalendModernizationPipeline") -> Any:
    """
    Returns existing active SparkSession or creates a new one with Delta support.
    """
    if SparkSession is None:
        raise RuntimeError("pyspark is not installed in the current Python environment.")

    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.mapKeyDedupPolicy.enabled", "true")
    )
    return builder.getOrCreate()


def get_table_fqn(layer: str, table_name: str, config: Optional[Dict[str, Any]] = None) -> str:
    """
    Constructs the fully-qualified 3-level Unity Catalog identifier (catalog.schema.table).
    """
    if config is None:
        config = load_config()

    catalog = config.get("catalog", "vente_catalog")
    schema = config.get("schemas", {}).get(layer, layer)
    return f"{catalog}.{schema}.{table_name}"
