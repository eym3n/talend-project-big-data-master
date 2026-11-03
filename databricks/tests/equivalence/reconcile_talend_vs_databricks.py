"""
Automated Equivalence and Parallel-Run Reconciliation Framework.
Compares legacy PostgreSQL (VENTE_ODS / VENTE_DWH) and Databricks Delta (silver / gold) outputs.
"""

import os
import sys
import psycopg2
from typing import Dict, Any, List, Tuple

from databricks.src.common.session import get_spark_session, load_config, get_table_fqn
from databricks.src.common.audit import PipelineAuditTracker


class ParallelRunReconciler:
    """
    Automated comparator executing row count, metric sum, and reject parity checks.
    """

    def __init__(self, pg_conn_params: Dict[str, Any], config_path: Optional[str] = None):
        self.pg_params = pg_conn_params
        self.config = load_config(config_path)
        self.spark = get_spark_session()
        self.tracker = PipelineAuditTracker("EquivalenceReconciliationEngine")

    def query_pg(self, query: str) -> List[Tuple]:
        conn = psycopg2.connect(**self.pg_params)
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    def run_reconciliation(self) -> Dict[str, Any]:
        self.tracker.start()
        results = {}
        all_passed = True

        print("\n>>> Executing Parallel Run Equivalence Gate Checks...\n")

        # Check 1: Fact Table Row Count Parity
        pg_fact_rows = self.query_pg('SELECT COUNT(*) FROM "VENTE_DWH"."FAIT_VENTE"')[0][0]
        dbx_fact_fqn = get_table_fqn("gold", "fact_vente", self.config)
        dbx_fact_rows = self.spark.table(dbx_fact_fqn).count()

        fact_row_pass = (pg_fact_rows == dbx_fact_rows)
        all_passed = all_passed and fact_row_pass
        print(f"Fact Table Row Count    | Legacy PG: {pg_fact_rows} | Databricks Delta: {dbx_fact_rows} | Pass: {fact_row_pass}")

        # Check 2: Financial Gross Revenue Sum Parity
        pg_revenue = float(self.query_pg('SELECT COALESCE(SUM("NB_MT_VENTE"), 0) FROM "VENTE_DWH"."FAIT_VENTE"')[0][0])
        dbx_revenue = float(self.spark.table(dbx_fact_fqn).selectExpr("COALESCE(SUM(NB_MT_VENTE), 0)").collect()[0][0])

        revenue_pass = abs(pg_revenue - dbx_revenue) < 0.01
        all_passed = all_passed and revenue_pass
        print(f"Gross Revenue Sum ($)  | Legacy PG: {pg_revenue:.2f} | Databricks Delta: {dbx_revenue:.2f} | Pass: {revenue_pass}")

        # Check 3: Financial Wholesale Cost Sum Parity
        pg_cost = float(self.query_pg('SELECT COALESCE(SUM("NB_MT_ACHAT"), 0) FROM "VENTE_DWH"."FAIT_VENTE"')[0][0])
        dbx_cost = float(self.spark.table(dbx_fact_fqn).selectExpr("COALESCE(SUM(NB_MT_ACHAT), 0)").collect()[0][0])

        cost_pass = abs(pg_cost - dbx_cost) < 0.01
        all_passed = all_passed and cost_pass
        print(f"Wholesale Cost Sum ($) | Legacy PG: {pg_cost:.2f} | Databricks Delta: {dbx_cost:.2f} | Pass: {cost_pass}")

        # Check 4: Total Units Sold Parity
        pg_units = int(self.query_pg('SELECT COALESCE(SUM("NB_QTE_VENTE"), 0) FROM "VENTE_DWH"."FAIT_VENTE"')[0][0])
        dbx_units = int(self.spark.table(dbx_fact_fqn).selectExpr("COALESCE(SUM(NB_QTE_VENTE), 0)").collect()[0][0])

        units_pass = (pg_units == dbx_units)
        all_passed = all_passed and units_pass
        print(f"Total Units Sold       | Legacy PG: {pg_units} | Databricks Delta: {dbx_units} | Pass: {units_pass}")

        # Check 5: Rejections & Quarantine Parity
        pg_rejects = self.query_pg('SELECT COUNT(*) FROM "VENTE_ODS"."ODS_REJET"')[0][0]
        dbx_quarantine_fqn = get_table_fqn("silver", "silver_quarantine_rejets", self.config)
        dbx_rejects = self.spark.table(dbx_quarantine_fqn).count() if self.spark.catalog.tableExists(dbx_quarantine_fqn) else 0

        reject_pass = (pg_rejects == dbx_rejects)
        all_passed = all_passed and reject_pass
        print(f"Quarantine Rejects     | Legacy PG: {pg_rejects} | Databricks Delta: {dbx_rejects} | Pass: {reject_pass}")

        status_str = "PASS" if all_passed else "FAIL"
        self.tracker.record_metric("Equivalence Overall Status", status_str)
        self.tracker.finish()

        return {
            "overall_status": status_str,
            "checks": {
                "fact_row_count": {"pg": pg_fact_rows, "dbx": dbx_fact_rows, "pass": fact_row_pass},
                "gross_revenue": {"pg": pg_revenue, "dbx": dbx_revenue, "pass": revenue_pass},
                "wholesale_cost": {"pg": pg_cost, "dbx": dbx_cost, "pass": cost_pass},
                "total_units": {"pg": pg_units, "dbx": dbx_units, "pass": units_pass},
                "quarantine_rejects": {"pg": pg_rejects, "dbx": dbx_rejects, "pass": reject_pass}
            }
        }


if __name__ == "__main__":
    pg_params = {
        "host": os.getenv("PGHOST", "localhost"),
        "port": os.getenv("PGPORT", "5432"),
        "dbname": os.getenv("PGDATABASE", "vente_db"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", "postgres")
    }
    reconciler = ParallelRunReconciler(pg_params)
    res = reconciler.run_reconciliation()
    sys.exit(0 if res["overall_status"] == "PASS" else 1)
