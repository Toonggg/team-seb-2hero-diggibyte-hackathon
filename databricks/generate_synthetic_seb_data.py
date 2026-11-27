# Databricks notebook source
# MAGIC %md
# MAGIC # SEB Kort — Synthetic Customer Conversations Generator (`dbldatagen`)
# MAGIC
# MAGIC Generates scalable synthetic customer-service conversation data (100k–1M+ rows) on Spark
# MAGIC matching the **SEB Kort Hackathon schema** across all 3 personas (`private_cardholder`,
# MAGIC `corporate_cardholder`, `corporate_administrator`) with realistic weekly spikes and CSAT distributions.
# MAGIC
# MAGIC **How to use:**
# MAGIC - Import this file into Databricks via **Git Folders (Repos)**, OR copy-paste each cell into a **Serverless Notebook**.
# MAGIC - Set `CATALOG` and `SCHEMA` in Cell 2 to your team's Unity Catalog target.

# COMMAND ----------

# MAGIC %pip install dbldatagen

# COMMAND ----------

import dbldatagen as dg
from pyspark.sql import functions as F

# --- Configuration (update to your team's Unity Catalog & row count) ---
CATALOG = "main"
SCHEMA = "seb_hackathon"
TABLE_NAME = f"{CATALOG}.{SCHEMA}.synthetic_conversations_scaled"
NUM_ROWS = 100_000  # Scale easily to 1_000_000+

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# COMMAND ----------

# Build synthetic conversations mirroring SEB Kort's 3 personas & 12-week window (2026-W37..W48)
weeks = [f"2026-W{w}" for w in range(37, 49)]

spec = (
    dg.DataGenerator(spark, name="seb_kort_conversations", rows=NUM_ROWS, partitions=8)
    .withIdOutput()
    .withColumn(
        "persona",
        "string",
        values=["private_cardholder", "corporate_cardholder", "corporate_administrator"],
        weights=[0.57, 0.24, 0.19],
        random=True,
    )
    .withColumn(
        "channel",
        "string",
        values=["phone", "chat", "email"],
        weights=[0.54, 0.32, 0.14],
        random=True,
    )
    .withColumn(
        "language",
        "string",
        values=["sv", "en", "no", "da"],
        weights=[0.62, 0.22, 0.09, 0.07],
        random=True,
    )
    .withColumn(
        "week_iso",
        "string",
        values=weeks,
        # Slight upward contact volume trend in W46-W48 (matching hackathon pattern)
        weights=[7, 7, 8, 8, 9, 9, 9, 9, 9, 10, 11, 12],
        random=True,
    )
    .withColumn("duration_sec", "integer", minValue=45, maxValue=1400, distribution="gamma(2.0, 2.0)", random=True)
    .withColumn("wait_time_sec", "integer", minValue=0, maxValue=900, distribution="gamma(1.5, 2.0)", random=True)
    .withColumn("after_hours", "boolean", expr="rand() < 0.18")
    .withColumn("bot_handled", "boolean", expr="channel = 'chat' AND rand() < 0.35")
    .withColumn("handover_to_agent", "boolean", expr="bot_handled AND rand() < 0.45")
    .withColumn("abandoned", "boolean", expr="wait_time_sec > 600 AND rand() < 0.25")
    .withColumn("transfer_count", "integer", values=[0, 1, 2], weights=[0.78, 0.18, 0.04], random=True)
    .withColumn("agent_tenure_band", "string", values=["<6m", "6–24m", ">24m"], weights=[0.20, 0.45, 0.35], random=True)
    .withColumn(
        "disposition_code",
        "string",
        values=[
            "Faktura",
            "Bedrägeri/reklamation",
            "App/inloggning",
            "Köp nekat",
            "Spärr/kort",
            "Bonus",
            "Receipts",
            "KYC/AML",
            "Card mgmt",
            "Limit",
        ],
        weights=[0.17, 0.15, 0.12, 0.12, 0.10, 0.08, 0.08, 0.07, 0.06, 0.05],
        random=True,
    )
    .withColumn("resolved_first_contact", "boolean", expr="rand() < 0.72")
    .withColumn("escalated", "boolean", expr="NOT resolved_first_contact AND rand() < 0.35")
    .withColumn("case_created", "boolean", expr="escalated OR rand() < 0.22")
    # ~30% CSAT response rate (1..5), lower when wait time is long or escalated
    .withColumn(
        "csat_score",
        "integer",
        expr="""
            CASE
              WHEN rand() > 0.30 THEN NULL
              WHEN escalated OR wait_time_sec > 480 THEN CAST(1 + floor(rand() * 2) AS INT)
              WHEN resolved_first_contact THEN CAST(3 + floor(rand() * 3) AS INT)
              ELSE CAST(2 + floor(rand() * 3) AS INT)
            END
        """,
    )
)

df_raw = spec.build()

# Add formatted conversation_id & realistic sentiment proxy aligned with CSAT/escalation
df = (
    df_raw.withColumn(
        "conversation_id",
        F.concat(F.lit("CONV-"), F.regexp_replace("week_iso", "-", ""), F.lit("-"), F.lpad(F.col("id").cast("string"), 6, "0")),
    )
    .withColumn(
        "sentiment_label",
        F.when(F.col("csat_score").isin(4, 5), "positive")
        .when(F.col("csat_score").isin(1, 2) | F.col("escalated") | F.col("abandoned"), "negative")
        .otherwise("neutral"),
    )
    .withColumn(
        "wait_time_sec",
        F.when(F.col("channel") == "email", F.lit(None).cast("int")).otherwise(F.col("wait_time_sec")),
    )
    .drop("id")
)

display(df.limit(10))

# COMMAND ----------

# Save to Unity Catalog Delta Table
df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(TABLE_NAME)
print(f"Wrote {df.count():,} synthetic SEB Kort rows to {TABLE_NAME}")

# COMMAND ----------

# Quick weekly summary check (verify distribution & CSAT by persona)
summary_df = (
    spark.table(TABLE_NAME)
    .groupBy("week_iso", "persona")
    .agg(
        F.count("*").alias("contacts"),
        F.round(F.avg("csat_score"), 2).alias("avg_csat"),
        F.round(100.0 * F.avg(F.when(F.col("sentiment_label") == "negative", 1).otherwise(0)), 1).alias("negative_pct"),
    )
    .orderBy("week_iso", "persona")
)
display(summary_df)
