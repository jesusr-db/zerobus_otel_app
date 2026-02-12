from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal
import logging
from server.models.observability import ServiceHealth, ServiceMetricsDetail
from server.services.lakebase_manager import LakebaseManager
from server.config import LAKEBASE_SCHEMA_NAME

logger = logging.getLogger(__name__)
router = APIRouter()

TimeRange = Literal["5m", "1h", "1d", "1w"]


def get_time_range_interval(time_range: TimeRange) -> tuple[str, int]:
    """
    Convert time range to SQL interval string and seconds.
    Returns (interval_string, seconds)

    Note: PostgreSQL requires lowercase with plural forms for quantities > 1
    """
    intervals = {
        "5m": ("5 minutes", 300),
        "1h": ("1 hour", 3600),
        "1d": ("1 day", 86400),
        "1w": ("7 days", 604800),
    }
    return intervals[time_range]


@router.get("/list")
async def get_services(
    request: Request,
    time_range: TimeRange = Query(default="1h", description="Time range for metrics")
) -> list[ServiceHealth]:
    user_token = request.headers.get("X-Forwarded-Access-Token")
    data_manager = LakebaseManager(user_token=user_token)
    interval, seconds = get_time_range_interval(time_range)

    # Use Lakebase (PostgreSQL) backend only
    # Optimized single-pass query on traces_silver_synced
    query = f"""
        SELECT
          service_name,
          PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as current_latency_p50,
          PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as current_latency_p95,
          PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as current_latency_p99,
          AVG(duration_ms) as avg_duration_ms,
          MAX(duration_ms) as max_duration_ms,
          SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
          COUNT(*) as request_count,
          CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) as error_rate,
          COUNT(*) / {seconds}.0 as requests_per_second,
          CASE
            WHEN SUM(CASE WHEN is_error THEN 1 ELSE 0 END) > 0 THEN 'critical'
            ELSE 'healthy'
          END as health_status
        FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
        WHERE start_timestamp >= NOW() - INTERVAL '{interval}'
          AND service_name IS NOT NULL
        GROUP BY service_name
        ORDER BY request_count DESC
        LIMIT 50
        """
    
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


@router.get("/{service_name}/metrics")
async def get_service_metrics(
    request: Request,
    service_name: str,
    time_range: TimeRange = Query(default="1h", description="Time range for metrics")
) -> ServiceMetricsDetail:
    from server.routers.metrics_kpis import get_bucket_size

    user_token = request.headers.get("X-Forwarded-Access-Token")
    lakebase_manager = LakebaseManager(user_token=user_token)
    interval, seconds = get_time_range_interval(time_range)
    bucket_interval, bucket_seconds = get_bucket_size(time_range)

    # Query traces_silver_synced directly (real-time individual spans)
    current_query = f"""
    SELECT
      COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms), 0.0) as latency_p50,
      COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms), 0.0) as latency_p95,
      COALESCE(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms), 0.0) as latency_p99,
      COALESCE(AVG(duration_ms), 0.0) as avg_duration_ms,
      COALESCE(MAX(duration_ms), 0.0) as max_duration_ms,
      COALESCE(SUM(CASE WHEN is_error THEN 1 ELSE 0 END), 0) as error_count,
      COALESCE(CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0), 0.0) as error_rate,
      COALESCE(COUNT(*), 0) as request_count,
      COALESCE(COUNT(*) / {seconds}, 0.0) as requests_per_second
    FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
    WHERE service_name = '{service_name}'
      AND start_timestamp >= NOW() - INTERVAL '{interval}'
    """

    trends_query = f"""
    SELECT
      to_timestamp(floor(extract(epoch from start_timestamp) / {bucket_seconds}) * {bucket_seconds}) as timestamp,
      PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
      AVG(duration_ms) as avg_duration_ms,
      SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
      COUNT(*) as request_count
    FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
    WHERE service_name = '{service_name}'
      AND start_timestamp >= NOW() - INTERVAL '{interval}'
    GROUP BY to_timestamp(floor(extract(epoch from start_timestamp) / {bucket_seconds}) * {bucket_seconds})
    ORDER BY timestamp
    """

    baseline_query = f"""
    SELECT
      COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms), 0.0) as latency_p50,
      COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms), 0.0) as latency_p95,
      COALESCE(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms), 0.0) as latency_p99,
      COALESCE(AVG(duration_ms), 0.0) as avg_duration_ms,
      COALESCE(MAX(duration_ms), 0.0) as max_duration_ms,
      COALESCE(SUM(CASE WHEN is_error THEN 1 ELSE 0 END), 0) as error_count,
      COALESCE(CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0), 0.0) as error_rate,
      COALESCE(COUNT(*), 0) as request_count,
      COALESCE(COUNT(*) / {seconds}, 0.0) as requests_per_second
    FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
    WHERE service_name = '{service_name}'
      AND start_timestamp >= NOW() - INTERVAL '{interval}' * 2
      AND start_timestamp < NOW() - INTERVAL '{interval}'
    """

    try:
        from server.models.observability import MetricsSnapshot, MetricsTimeSeries

        current_results = lakebase_manager.execute_query(current_query)
        trends_results = lakebase_manager.execute_query(trends_query)
        baseline_results = lakebase_manager.execute_query(baseline_query)

        if not current_results:
            raise HTTPException(status_code=404, detail=f"No data found for service: {service_name}")

        current = MetricsSnapshot(**current_results[0])
        trends = [MetricsTimeSeries(**row) for row in trends_results]
        baseline = MetricsSnapshot(**baseline_results[0]) if baseline_results else current

        return ServiceMetricsDetail(
            service_name=service_name,
            current=current,
            trends=trends,
            baseline=baseline
        )
    except Exception as e:
        logger.error(f"Metrics query failed for {service_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/{service_name}/dependencies")
async def get_service_dependencies(
    request: Request,
    service_name: str,
    time_range: TimeRange = Query(default="1h", description="Time range for dependencies")
):
    from server.models.observability import ServiceDependencies, DependencyInfo

    user_token = request.headers.get("X-Forwarded-Access-Token")
    lakebase_manager = LakebaseManager(user_token=user_token)
    interval, _ = get_time_range_interval(time_range)

    # Filter dependencies by last_seen within time range
    query = f"""
    SELECT
      'inbound' as direction,
      source_service as service_name,
      call_count,
      'healthy' as health_status
    FROM {LAKEBASE_SCHEMA_NAME}.service_dependencies_synced
    WHERE target_service = '{service_name}'
      AND last_seen >= NOW() - INTERVAL '{interval}'
    UNION ALL
    SELECT
      'outbound' as direction,
      target_service as service_name,
      call_count,
      'healthy' as health_status
    FROM {LAKEBASE_SCHEMA_NAME}.service_dependencies_synced
    WHERE source_service = '{service_name}'
      AND last_seen >= NOW() - INTERVAL '{interval}'
    ORDER BY direction, call_count DESC
    """

    try:
        results = lakebase_manager.execute_query(query)
        if not results:
            logger.info(f"No dependencies found for service: {service_name}")
            return ServiceDependencies(
                service_name=service_name,
                inbound=[],
                outbound=[]
            )

        inbound = [
            DependencyInfo(
                service_name=row['service_name'],
                call_count=row['call_count'],
                health_status=row['health_status']
            )
            for row in results if row['direction'] == 'inbound'
        ]

        outbound = [
            DependencyInfo(
                service_name=row['service_name'],
                call_count=row['call_count'],
                health_status=row['health_status']
            )
            for row in results if row['direction'] == 'outbound'
        ]

        return ServiceDependencies(
            service_name=service_name,
            inbound=inbound,
            outbound=outbound
        )
    except Exception as e:
        logger.error(f"Dependencies query failed for {service_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/{service_name}/traces")
async def get_service_traces(
    request: Request,
    service_name: str,
    time_range: TimeRange = Query(default="1h", description="Time range for traces")
):
    from server.models.observability import TraceInfo

    user_token = request.headers.get("X-Forwarded-Access-Token")
    lakebase_manager = LakebaseManager(user_token=user_token)
    interval, seconds = get_time_range_interval(time_range)

    # Optimized query - filter by service and aggregate in one pass
    query = f"""
    SELECT
      trace_id,
      MIN(start_timestamp) as trace_start,
      ARRAY_AGG(DISTINCT service_name) as services_involved,
      COUNT(*) as span_count,
      SUM(duration_ms) as total_duration_ms
    FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
    WHERE service_name = '{service_name}'
      AND start_timestamp >= NOW() - INTERVAL '{interval}'
    GROUP BY trace_id
    ORDER BY trace_start DESC
    LIMIT 50
    """

    try:
        results = lakebase_manager.execute_query(query)
        if not results:
            logger.info(f"No traces found for service: {service_name}")
            return []

        return [TraceInfo(**row) for row in results]
    except Exception as e:
        logger.error(f"Traces query failed for {service_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/traces/{trace_id}")
async def get_trace_detail(
    request: Request,
    trace_id: str
):
    from server.models.observability import TraceDetail, SpanDetail

    user_token = request.headers.get("X-Forwarded-Access-Token")
    lakebase_manager = LakebaseManager(user_token=user_token)

    # Query traces_silver_synced directly for all trace info
    trace_query = f"""
    SELECT
      trace_id,
      MIN(start_timestamp) as trace_start
    FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
    WHERE trace_id = '{trace_id}'
    GROUP BY trace_id
    """

    spans_query = f"""
    SELECT
      service_name,
      SUM(duration_ms) as total_duration_ms
    FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
    WHERE trace_id = '{trace_id}'
    GROUP BY service_name
    ORDER BY total_duration_ms DESC
    """

    try:
        trace_results = lakebase_manager.execute_query(trace_query)
        if not trace_results:
            raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")

        spans_results = lakebase_manager.execute_query(spans_query)

        return TraceDetail(
            trace_id=trace_results[0]['trace_id'],
            trace_start=trace_results[0]['trace_start'],
            spans=[SpanDetail(**row) for row in spans_results]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trace detail query failed for {trace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
