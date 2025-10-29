from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal
import logging
from server.models.observability import ServiceHealth, ServiceMetricsDetail
from server.services.warehouse_manager import WarehouseManager
from server.config import OBSERVABILITY_TABLE_PREFIX

logger = logging.getLogger(__name__)
router = APIRouter()

TimeRange = Literal["15m", "1h", "24h"]


def get_time_range_interval(time_range: TimeRange) -> tuple[str, int]:
    intervals = {
        "15m": ("15 MINUTE", 900),
        "1h": ("1 HOUR", 3600),
        "24h": ("24 HOUR", 86400),
    }
    return intervals[time_range]


@router.get("/list")
async def get_services(
    request: Request,
    time_range: TimeRange = Query(default="1h", description="Time range for metrics")
) -> list[ServiceHealth]:
    user_token = request.headers.get("X-Forwarded-Access-Token")
    warehouse_manager = WarehouseManager(user_token=user_token)
    interval, seconds = get_time_range_interval(time_range)
    
    query = f"""
    WITH service_spans AS (
      SELECT 
        span.service_name,
        span.duration_ms,
        span.is_error,
        t.trace_start
      FROM jmr_demo.zerobus.traces_assembled_silver t
      LATERAL VIEW explode(span_details) AS span
      WHERE t.trace_start >= NOW() - INTERVAL {interval}
    ),
    service_metrics AS (
      SELECT
        service_name,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as latency_p50,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
        PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as latency_p99,
        AVG(duration_ms) as avg_duration,
        MAX(duration_ms) as max_duration,
        SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
        COUNT(*) as request_count
      FROM service_spans
      GROUP BY service_name
    )
    SELECT 
      service_name,
      latency_p50 as current_latency_p50,
      latency_p95 as current_latency_p95,
      latency_p99 as current_latency_p99,
      avg_duration as avg_duration_ms,
      max_duration as max_duration_ms,
      error_count,
      request_count,
      CAST(error_count AS FLOAT) / NULLIF(request_count, 0) as error_rate,
      request_count / {seconds} as requests_per_second,
      CASE 
        WHEN CAST(error_count AS FLOAT) / NULLIF(request_count, 0) > 0.05 THEN 'critical'
        WHEN CAST(error_count AS FLOAT) / NULLIF(request_count, 0) > 0.01 THEN 'warning'
        ELSE 'healthy'
      END as health_status
    FROM service_metrics
    ORDER BY request_count DESC
    """
    
    try:
        results = warehouse_manager.execute_query(query)
        if not results:
            logger.warning("Query returned no results")
            return []
        logger.info(f"Query returned {len(results)} services")
        return [ServiceHealth(**row) for row in results]
    except Exception as e:
        logger.error(f"Services query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/{service_name}/metrics")
async def get_service_metrics(
    service_name: str,
    time_range: TimeRange = Query(default="1h", description="Time range for metrics")
) -> ServiceMetricsDetail:
    raise HTTPException(status_code=501, detail="Not implemented yet - Phase 3")


@router.get("/{service_name}/dependencies")
async def get_service_dependencies(service_name: str):
    raise HTTPException(status_code=501, detail="Not implemented yet - Phase 2")
