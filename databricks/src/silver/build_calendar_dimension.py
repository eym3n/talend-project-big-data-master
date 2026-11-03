"""
Silver Calendar Dimension Generator Module.
Modernizes jGenerateCalendar and replaces joursFeries.xlsx dependency with native Spark functions and holiday logic.
"""

from datetime import date
from typing import Dict, Any, Optional
from pyspark.sql import DataFrame
from pyspark.sql.types import (
    StructType,
    StructField,
    IntegerType,
    DateType,
    StringType
)
from pyspark.sql.functions import (
    col,
    date_format,
    year,
    month,
    dayofmonth,
    dayofyear,
    dayofweek,
    weekofyear,
    quarter,
    last_day,
    when,
    lit,
    sequence,
    explode,
    to_date
)

from ..common.session import get_spark_session, load_config, get_table_fqn
from ..common.holidays import FrenchHolidaysCalculator


FRENCH_MONTHS = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}

FRENCH_DAYS = {
    1: "Dimanche", 2: "Lundi", 3: "Mardi", 4: "Mercredi",
    5: "Jeudi", 6: "Vendredi", 7: "Samedi"
}


def build_calendar_dimension(
    start_date: str = "2020-01-01",
    end_date: str = "2030-12-31",
    config: Optional[Dict[str, Any]] = None
) -> DataFrame:
    """
    Generates the complete enterprise date dimension table (silver.dim_calendrier).
    """
    if config is None:
        config = load_config()

    spark = get_spark_session()
    target_fqn = get_table_fqn("silver", "dim_calendrier", config)

    # 1. Generate continuous date sequence
    df_dates = (
        spark.sql(f"SELECT explode(sequence(to_date('{start_date}'), to_date('{end_date}'), interval 1 day)) as DT_JOUR")
    )

    # 2. Extract base date features
    df_features = (
        df_dates
        .withColumn("ID_DIM_CALENDRIER", date_format(col("DT_JOUR"), "yyyyMMdd").cast(IntegerType()))
        .withColumn("NB_ANNEE", year(col("DT_JOUR")))
        .withColumn("NB_MOIS", month(col("DT_JOUR")))
        .withColumn("NB_TRIMESTRE", quarter(col("DT_JOUR")))
        .withColumn("NB_SEMESTRE", when(col("NB_MOIS") <= 6, lit(1)).otherwise(lit(2)))
        .withColumn("NB_JOUR_ANNEE", dayofyear(col("DT_JOUR")))
        .withColumn("NB_JOUR_MOIS", dayofmonth(col("DT_JOUR")))
        .withColumn("NB_JOUR_SEMAINE", dayofweek(col("DT_JOUR")))
        .withColumn("NB_SEMAINE_ANNEE", weekofyear(col("DT_JOUR")))
        .withColumn("BL_DERNIER_JOUR_MOIS", when(col("DT_JOUR") == last_day(col("DT_JOUR")), lit(1)).otherwise(lit(0)))
        .withColumn(
            "BL_BISSEXTILE",
            when(
                ((col("NB_ANNEE") % 4 == 0) & (col("NB_ANNEE") % 100 != 0)) | (col("NB_ANNEE") % 400 == 0),
                lit(1)
            ).otherwise(lit(0))
        )
        .withColumn(
            "BL_WEEK_END",
            when(col("NB_JOUR_SEMAINE").isin(1, 7), lit(1)).otherwise(lit(0))
        )
    )

    # 3. Apply French month and weekday labels
    month_expr = when(col("NB_MOIS") == 1, lit(FRENCH_MONTHS[1]))
    for m in range(2, 13):
        month_expr = month_expr.when(col("NB_MOIS") == m, lit(FRENCH_MONTHS[m]))
    df_labeled = df_features.withColumn("LB_MOIS", month_expr)

    day_expr = when(col("NB_JOUR_SEMAINE") == 1, lit(FRENCH_DAYS[1]))
    for d in range(2, 8):
        day_expr = day_expr.when(col("NB_JOUR_SEMAINE") == d, lit(FRENCH_DAYS[d]))
    df_labeled = df_labeled.withColumn("LB_JOUR", day_expr)

    # 4. Integrate Public Holidays
    start_year = int(start_date.split("-")[0])
    end_year = int(end_date.split("-")[0])
    holidays_dict = FrenchHolidaysCalculator.get_holidays_range(start_year, end_year)

    holidays_rows = [(d, name) for d, name in holidays_dict.items()]
    holiday_schema = StructType([
        StructField("H_DATE", DateType(), False),
        StructField("LB_JOUR_FERIE", StringType(), False)
    ])
    df_holidays = spark.createDataFrame(holidays_rows, holiday_schema)

    df_final = (
        df_labeled.join(
            df_holidays,
            col("DT_JOUR") == col("H_DATE"),
            how="left"
        )
        .withColumn("BL_JOUR_FERIE", when(col("LB_JOUR_FERIE").isNotNull(), lit(1)).otherwise(lit(0)))
        .drop("H_DATE")
        .select(
            "ID_DIM_CALENDRIER",
            "DT_JOUR",
            "NB_ANNEE",
            "NB_SEMESTRE",
            "NB_TRIMESTRE",
            "NB_MOIS",
            "NB_JOUR_ANNEE",
            "NB_JOUR_MOIS",
            "NB_JOUR_SEMAINE",
            "NB_SEMAINE_ANNEE",
            "LB_MOIS",
            "LB_JOUR",
            "BL_DERNIER_JOUR_MOIS",
            "BL_BISSEXTILE",
            "BL_WEEK_END",
            "BL_JOUR_FERIE",
            "LB_JOUR_FERIE"
        )
    )

    # Write to Silver Delta table (Overwrite to ensure clean idempotent dimension)
    df_final.write.format("delta").mode("overwrite").saveAsTable(target_fqn)
    return df_final
