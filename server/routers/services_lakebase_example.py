"""
Example: services.py router updated for Lakebase support

This file demonstrates how to update services.py to use LakebaseManager.
Key changes:
1. Import LakebaseManager and SQL converter
2. Use DATA_BACKEND config to choose manager
3. Convert queries using sql_converter
4. Update table references to use _synced suffix
"""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal
import logging
from server.models.observability import ServiceHealth, ServiceMetricsDetail
from server.services.warehouse_manager import WarehouseManager
from server.services.lakebase_manager import LakebaseManager
from server.services.sql_converter import convert_spark_to_postgres
from server.config import OBSERVABILITY_TABLE_PREFIX, DATA_BACKEND

logger = logging.getLogger(__name__)
router = APIRouter()

TimeRange = Literal["1h", "24h"]


def get_time_range_interval(time_range: TimeRange) -> tuple[str, int]:
    intervals = {
        "1h": ("1 hour", 3600),  # PostgreSQL lowercase
        "24h": ("24 hour", 86400),
    }
    return intervals[time_range]


def get_data_manager(user_token: str = None):
    """Factory function to return appropriate data manager based on config."""
    if DATA_BACKEND == "lakebase":
        return LakebaseManager(user_token=user_token)
    else:
        return WarehouseManager(user_token=user_token)


@router.get("/list")
async def get_services(
    request: Request,
    time_range: TimeRange = Query(default="1h", description="Time range for metrics")
) -> list[ServiceHealth]:
    user_token = request.headers.get("X-Forwarded-Access-Token")
    data_manager = get_data_manager(user_token)
    interval, seconds = get_time_range_interval(time_range)
    
    # Original Spark SQL query
    spark_query = f"""
    WITH current_spans AS (
      SELECT 
        span.service_name,
        span.duration_ms,
        span.is_error,
        t.trace_start
      FROM {OBSERVABILITY_TABLE_PREFIX}.traces_assembled_silver t
      LATERAL VIEW explode(span_details) AS span
      WHERE t.trace_start >= NOW() - INTERVAL {interval}
    ),
    baseline_spans AS (
      SELECT 
        span.service_name,
        span.duration_ms
      FROM {OBSERVABILITY_TABLE_PREFIX}.traces_assembled_silver t
      LATERAL VIEW explode(span_details) AS span
      WHERE t.trace_start >= NOW() - INTERVAL {interval} * 2
        AND t.trace_start < NOW() - INTERVAL {interval}
    ),
    current_metrics AS (
      SELECT
        service_name,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as latency_p50,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
        PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as latency_p99,
        AVG(duration_ms) as avg_duration,
        MAX(duration_ms) as max_duration,
        SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
        COUNT(*) as request_count
      FROM current_spans
      GROUP BY service_name
    ),
    baseline_metrics AS (
      SELECT
        service_name,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as baseline_latency_p50,
        COUNT(*) / {seconds} as baseline_rps
      FROM baseline_spans
      GROUP BY service_name
    )
    SELECT 
      c.service_name,
      c.latency_p50 as current_latency_p50,
      c.latency_p95 as current_latency_p95,
      c.latency_p99 as current_latency_p99,
      c.avg_duration as avg_duration_ms,
      c.max_duration as max_duration_ms,
      c.error_count,
      c.request_count,
      CAST(c.error_count AS FLOAT) / NULLIF(c.request_count, 0) as error_rate,
      c.request_count / {seconds} as requests_per_second,
      CASE 
        WHEN c.latency_p50 > COALESCE(b.baseline_latency_p50, c.latency_p50) THEN 'critical'
        WHEN c.request_count / {seconds} > COALESCE(b.baseline_rps, c.request_count / {seconds}) THEN 'warning'
        ELSE 'healthy'
      END as health_status
    FROM current_metrics c
    LEFT JOIN baseline_metrics b ON c.service_name = b.service_name
    ORDER BY c.request_count DESC
    """
    
    # Convert query if using Lakebase
    if DATA_BACKEND == "lakebase":
        query = convert_spark_to_postgres(spark_query)
        logger.info("Using Lakebase backend with converted query")
    else:
        query = spark_query
        logger.info("Using SQL Warehouse backend")
    
    try:
        results = data_manager.execute_query(query)
        if not results:
            logger.warning("Query returned no results")
            return []
        logger.info(f"Query returned {len(results)} services")
        return [ServiceHealth(**row) for row in results]
    except Exception as e:
        logger.error(f"Services query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# Similar pattern for other endpoints...
# get_service_metrics(), get_service_dependencies(), etc.
