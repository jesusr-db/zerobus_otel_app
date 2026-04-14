# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer - Aggregations and Analytics
# MAGIC
# MAGIC Gold layer tables for business intelligence, reporting, and anomaly detection.
# MAGIC Supports **streaming** (continuous) and **scheduled** (batch) modes via `pipeline_mode` config.
# MAGIC
# MAGIC **Inputs**:
# MAGIC - `{catalog}.zerobus_sdp.traces_silver` (streaming or batch read)
# MAGIC
# MAGIC **Outputs**:
# MAGIC - `{catalog}.zerobus_sdp.service_health_5min` (streaming or batch)
# MAGIC - `{catalog}.zerobus_sdp.service_health_hourly` (streaming or batch)
# MAGIC - `{catalog}.zerobus_sdp.service_dependencies` (always batch - periodic snapshot of dependency graph)
# MAGIC - `{catalog}.zerobus_sdp.traces_assembled` (streaming or batch)
# MAGIC - `{catalog}.zerobus_sdp.anomaly_baselines` (always batch - 7-day statistical window)
# MAGIC
# MAGIC **Mode selection**: Set `pipeline_mode` in pipeline configuration:
# MAGIC - `"streaming"` (default): All tables use readStream with watermarks, pipeline runs continuously
# MAGIC - `"scheduled"`: All tables use batch reads with time filters, pipeline triggered by job

# COMMAND ----------

import dlt
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql.window import Window

# Get configuration from pipeline settings
catalog_name = spark.conf.get("catalog_name", "jmr_demo")
schema_name = spark.conf.get("schema_name", "zerobus_sdp")
pipeline_mode = spark.conf.get("pipeline_mode", "streaming")
is_streaming = pipeline_mode == "streaming"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Service Health 5-Minute Windows
# MAGIC
# MAGIC Streaming computation from traces_silver with 5-minute tumbling windows.
# MAGIC
# MAGIC Supports both streaming (continuous) and batch (scheduled) modes via `pipeline_mode` config.
# MAGIC
# MAGIC Key improvements:
# MAGIC - 80% fewer rows than 1-minute windows (288 vs 1,440 rows/day per service)
# MAGIC - Single-pass percentile computation (not double aggregation)
# MAGIC - Correct statistical computation (percentiles on raw data)
# MAGIC - Gold layer placement (appropriate for aggregations)

# COMMAND ----------

@dlt.table(
    name="service_health_5min",
    comment="5-minute service health metrics computed directly from traces",
    table_properties={
        "quality": "gold",
        "pipelines.autoOptimize.managed": "true",
        "delta.enableChangeDataFeed": "true"
    }
)
def service_health_5min():
    """
    Streaming or batch computation from traces_silver with 5-minute windows.
    Mode controlled by pipeline_mode config variable.
    """
    source_table = f"{catalog_name}.{schema_name}.traces_silver"

    if is_streaming:
        traces = (
            spark.readStream.table(source_table)
            .withWatermark("start_timestamp", "10 minutes")
        )
    else:
        traces = spark.read.table(source_table).filter(
            col("start_timestamp") >= current_timestamp() - expr("INTERVAL 90 DAYS")
        )

    return (
        traces
        .groupBy(
            "service_name",
            window("start_timestamp", "5 minutes")
        )
        .agg(
            # Error rate calculation
            (sum(when(col("is_error") == True, 1).otherwise(0)) / count("*")).alias("error_rate"),

            # Latency percentiles - computed once from raw durations
            expr("percentile_approx(duration_ms, 0.50)").alias("p50_latency_ms"),
            expr("percentile_approx(duration_ms, 0.95)").alias("p95_latency_ms"),
            expr("percentile_approx(duration_ms, 0.99)").alias("p99_latency_ms"),

            # Basic stats
            count("*").alias("total_requests"),
            avg("duration_ms").alias("avg_latency_ms"),
            min("duration_ms").alias("min_latency_ms"),
            max("duration_ms").alias("max_latency_ms")
        )
        .withColumn("timestamp", col("window.start"))
        .withColumn("ingestion_timestamp", current_timestamp())
        .select(
            "timestamp",
            "service_name",
            "error_rate",
            "p50_latency_ms",
            "p95_latency_ms",
            "p99_latency_ms",
            "total_requests",
            "avg_latency_ms",
            "min_latency_ms",
            "max_latency_ms",
            "ingestion_timestamp"
        )
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Service Health Hourly Rollups
# MAGIC
# MAGIC Aggregate 5-minute windows to hourly using streaming or batch mode.

# COMMAND ----------

@dlt.table(
    name="service_health_hourly",
    comment="Hourly aggregated service health metrics (error rates, latency, request counts)",
    table_properties={
        "quality": "gold",
        "pipelines.autoOptimize.managed": "true"
    }
)
def service_health_hourly():
    """
    Aggregate 5-minute windows to hourly.
    Streaming mode chains from service_health_5min via dlt.read_stream.
    """
    if is_streaming:
        health_5min = (
            dlt.read_stream("service_health_5min")
            .withWatermark("timestamp", "70 minutes")
        )
    else:
        health_5min = dlt.read("service_health_5min").filter(
            col("timestamp") >= current_timestamp() - expr("INTERVAL 30 DAYS")
        )

    return (
        health_5min
        .groupBy(
            "service_name",
            window("timestamp", "1 hour")
        )
        .agg(
            # Weighted average for error rate (by request count)
            sum(col("error_rate") * col("total_requests")).alias("weighted_error_sum"),
            sum("total_requests").alias("total_requests"),

            # For percentiles: use max of 5-min p95/p99 as approximation
            max("p95_latency_ms").alias("p95_latency_ms"),
            max("p99_latency_ms").alias("p99_latency_ms"),

            # Simple aggregations
            avg("avg_latency_ms").alias("avg_latency_ms"),
            max("max_latency_ms").alias("max_latency_ms"),
            min("min_latency_ms").alias("min_latency_ms")
        )
        .withColumn("hour", col("window.start"))
        .withColumn("error_rate", col("weighted_error_sum") / col("total_requests"))
        .withColumn("ingestion_timestamp", current_timestamp())
        .select(
            "service_name",
            "hour",
            "error_rate",
            "p95_latency_ms",
            "p99_latency_ms",
            "avg_latency_ms",
            "total_requests",
            "ingestion_timestamp"
        )
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Service Dependencies Graph

# COMMAND ----------

@dlt.table(
    name="service_dependencies",
    comment="Service-to-service dependency graph with call counts and activity timestamps",
    table_properties={
        "quality": "gold",
        "pipelines.autoOptimize.managed": "true",
        "delta.enableChangeDataFeed": "true"
    }
)
def service_dependencies():
    """
    Build service-to-service dependency graph from parent-child span relationships.

    Always runs in batch mode regardless of pipeline_mode setting.
    The dependency graph is a periodic snapshot (one row per service pair),
    not a streaming append. In a continuous pipeline, DLT refreshes this
    periodically as a materialized view.

    Columns:
    - first_seen/last_seen: When this dependency was observed
    - call_count/unique_traces: Running totals of calls and traces
    """
    source_table = f"{catalog_name}.{schema_name}.traces_silver"

    traces = spark.read.table(source_table).filter(
        col("start_timestamp") >= current_timestamp() - expr("INTERVAL 90 DAYS")
    )

    service_last_active = (
        traces
        .groupBy("service_name")
        .agg(max("start_timestamp").alias("service_last_active"))
    )

    child_spans = traces.filter(col("parent_span_id").isNotNull()).alias("child")

    dependencies = (
        child_spans
        .join(
            traces.alias("parent"),
            (col("child.parent_span_id") == col("parent.span_id")) &
            (col("child.trace_id") == col("parent.trace_id")),
            "inner"
        )
        .select(
            col("parent.service_name").alias("source_service"),
            col("child.service_name").alias("target_service"),
            col("child.trace_id").alias("trace_id"),
            col("child.start_timestamp").alias("call_timestamp")
        )
    )

    deps_aggregated = (
        dependencies
        .groupBy("source_service", "target_service")
        .agg(
            count("*").alias("call_count"),
            countDistinct("trace_id").alias("unique_traces"),
            min("call_timestamp").alias("first_seen"),
            max("call_timestamp").alias("last_seen")
        )
    )

    result = (
        deps_aggregated
        .join(
            service_last_active.alias("src_activity"),
            col("source_service") == col("src_activity.service_name"),
            "left"
        )
        .withColumn("source_last_active", col("src_activity.service_last_active"))
        .drop("service_name", "service_last_active")
        .join(
            service_last_active.alias("tgt_activity"),
            col("target_service") == col("tgt_activity.service_name"),
            "left"
        )
        .withColumn("target_last_active", col("tgt_activity.service_last_active"))
        .drop("service_name", "service_last_active")
        .withColumn("last_active", greatest("source_last_active", "target_last_active"))
        .withColumn("ingestion_timestamp", current_timestamp())
        .select(
            "source_service",
            "target_service",
            "call_count",
            "unique_traces",
            "first_seen",
            "last_seen",
            "last_active",
            "ingestion_timestamp"
        )
    )

    return result

# COMMAND ----------

# MAGIC %md
# MAGIC ## Traces Assembled
# MAGIC
# MAGIC Streaming or batch aggregation of traces from traces_silver.
# MAGIC
# MAGIC **History**: Was originally streaming in silver but moved to batch due to:
# MAGIC - 2-minute watermark dropping late-arriving spans (too aggressive)
# MAGIC - 5-minute window grouping splitting traces across rows
# MAGIC
# MAGIC **Fix**: Now uses 15-minute watermark (handles late spans) and groups by
# MAGIC trace_id within a 15-minute tumbling window (keeps traces together without
# MAGIC unbounded state).

# COMMAND ----------

@dlt.table(
    name="traces_assembled",
    comment="Assembled traces with aggregated span information",
    table_properties={
        "quality": "gold",
        "pipelines.autoOptimize.managed": "true",
        "delta.enableChangeDataFeed": "true"
    }
)
def traces_assembled():
    """
    Streaming or batch aggregation of traces.

    Streaming mode: Uses 15-minute watermark (vs old 2-min that dropped data)
    and groups by trace_id within a 15-minute window to bound state while
    keeping most trace spans together.

    Batch mode: 24-hour lookback, groups by trace_id only.
    """
    source_table = f"{catalog_name}.{schema_name}.traces_silver"

    if is_streaming:
        traces = (
            spark.readStream.table(source_table)
            .withWatermark("start_timestamp", "15 minutes")
        )

        return (
            traces
            .groupBy(
                "trace_id",
                window("start_timestamp", "15 minutes")
            )
            .agg(
                count("*").alias("span_count"),
                min("start_timestamp").alias("trace_start"),
                max("end_timestamp").alias("trace_end"),
                collect_set("service_name").alias("services_involved"),
                sum(col("is_error").cast("int")).alias("error_count"),
                max("duration_ms").alias("max_span_duration_ms"),
                avg("duration_ms").alias("avg_span_duration_ms"),
                collect_list(
                    struct(
                        "span_id",
                        "parent_span_id",
                        "name",
                        "kind",
                        "service_name",
                        "duration_ms",
                        "is_error"
                    )
                ).alias("span_details")
            )
            .withColumn("has_errors", col("error_count") > 0)
            .withColumn("total_trace_duration_ms",
                        (unix_timestamp("trace_end") - unix_timestamp("trace_start")) * 1000)
            .withColumn("service_count", size("services_involved"))
            .withColumn("ingestion_timestamp", current_timestamp())
            .select(
                "trace_id",
                "span_count",
                "trace_start",
                "trace_end",
                "total_trace_duration_ms",
                "services_involved",
                "service_count",
                "error_count",
                "has_errors",
                "max_span_duration_ms",
                "avg_span_duration_ms",
                "span_details",
                "ingestion_timestamp"
            )
        )
    else:
        traces = spark.read.table(source_table).filter(
            col("start_timestamp") >= current_timestamp() - expr("INTERVAL 24 HOURS")
        )

        return (
            traces
            .groupBy("trace_id")
            .agg(
                count("*").alias("span_count"),
                min("start_timestamp").alias("trace_start"),
                max("end_timestamp").alias("trace_end"),
                collect_set("service_name").alias("services_involved"),
                sum(col("is_error").cast("int")).alias("error_count"),
                max("duration_ms").alias("max_span_duration_ms"),
                avg("duration_ms").alias("avg_span_duration_ms"),
                collect_list(
                    struct(
                        "span_id",
                        "parent_span_id",
                        "name",
                        "kind",
                        "service_name",
                        "duration_ms",
                        "is_error"
                    )
                ).alias("span_details")
            )
            .withColumn("has_errors", col("error_count") > 0)
            .withColumn("total_trace_duration_ms",
                        (unix_timestamp("trace_end") - unix_timestamp("trace_start")) * 1000)
            .withColumn("service_count", size("services_involved"))
            .withColumn("ingestion_timestamp", current_timestamp())
            .select(
                "trace_id",
                "span_count",
                "trace_start",
                "trace_end",
                "total_trace_duration_ms",
                "services_involved",
                "service_count",
                "error_count",
                "has_errors",
                "max_span_duration_ms",
                "avg_span_duration_ms",
                "span_details",
                "ingestion_timestamp"
            )
        )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Anomaly Detection Baselines
# MAGIC
# MAGIC Compute baselines from 5-minute data. Always runs in batch mode regardless of
# MAGIC pipeline_mode setting -- a 7-day statistical window doesn't benefit from streaming.
# MAGIC
# MAGIC In a continuous pipeline, this becomes a materialized view that refreshes periodically.

# COMMAND ----------

@dlt.table(
    name="anomaly_baselines",
    comment="Statistical baselines for service health anomaly detection (7-day rolling window)",
    table_properties={
        "quality": "gold",
        "pipelines.autoOptimize.managed": "true"
    }
)
def anomaly_baselines():
    """
    Compute baselines from 5-minute data.
    Always batch: reads the materialized service_health_5min table directly,
    not via streaming. In continuous mode, DLT refreshes this periodically.
    """
    # Always use batch read from the underlying table -- 7-day aggregation
    # is not suitable for streaming
    service_health_5min = spark.read.table(
        f"{catalog_name}.{schema_name}.service_health_5min"
    ).filter(
        col("timestamp") >= current_timestamp() - expr("INTERVAL 7 DAYS")
    )

    return (
        service_health_5min
        .groupBy("service_name")
        .agg(
            # Baseline statistics
            avg("error_rate").alias("baseline_error_rate"),
            stddev("error_rate").alias("error_rate_stddev"),
            avg("p95_latency_ms").alias("baseline_p95_latency_ms"),
            stddev("p95_latency_ms").alias("latency_stddev"),

            # Thresholds (3-sigma)
            (avg("error_rate") + 3 * stddev("error_rate")).alias("error_rate_threshold"),
            (avg("p95_latency_ms") + 3 * stddev("p95_latency_ms")).alias("latency_threshold"),

            # Metadata
            count("*").alias("sample_count"),
            min("timestamp").alias("baseline_start_timestamp"),
            max("timestamp").alias("baseline_end_timestamp")
        )
        .withColumn("baseline_computed_at", current_timestamp())
        .select(
            "service_name",
            "baseline_error_rate",
            "error_rate_stddev",
            "error_rate_threshold",
            "baseline_p95_latency_ms",
            "latency_stddev",
            "latency_threshold",
            "sample_count",
            "baseline_start_timestamp",
            "baseline_end_timestamp",
            "baseline_computed_at"
        )
    )

# COMMAND ----------
