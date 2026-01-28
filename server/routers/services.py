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
    # Native PostgreSQL query - combines traces, logs, and metrics
    # Uses traces_silver_synced (real-time individual spans) instead of traces_assembled_synced (batch)
    query = f"""
        WITH trace_services AS (
          SELECT DISTINCT
            service_name
          FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
          WHERE start_timestamp >= NOW() - INTERVAL '{interval}'
            AND service_name IS NOT NULL
        ),
        log_services AS (
          SELECT DISTINCT
            service_name
          FROM {LAKEBASE_SCHEMA_NAME}.logs_synced
          WHERE log_timestamp >= NOW() - INTERVAL '{interval}'
            AND service_name IS NOT NULL
        ),
        metric_services AS (
          SELECT DISTINCT
            service_name
          FROM {LAKEBASE_SCHEMA_NAME}.metrics_1min_synced
          WHERE window_start >= NOW() - INTERVAL '{interval}'
            AND service_name IS NOT NULL
        ),
        all_services AS (
          SELECT service_name FROM trace_services
          UNION
          SELECT service_name FROM log_services
          UNION
          SELECT service_name FROM metric_services
        ),
        current_spans AS (
          SELECT
            service_name,
            duration_ms,
            is_error,
            start_timestamp
          FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
          WHERE start_timestamp >= NOW() - INTERVAL '{interval}'
            AND service_name IS NOT NULL
        ),
        baseline_spans AS (
          SELECT
            service_name,
            duration_ms
          FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
          WHERE start_timestamp >= NOW() - INTERVAL '{interval}' * 2
            AND start_timestamp < NOW() - INTERVAL '{interval}'
            AND service_name IS NOT NULL
        ),
        log_error_counts AS (
          SELECT
            service_name,
            COUNT(*) as log_error_count
          FROM {LAKEBASE_SCHEMA_NAME}.logs_synced
          WHERE log_timestamp >= NOW() - INTERVAL '{interval}'
            AND service_name IS NOT NULL
            AND severity_text IN ('ERROR', 'FATAL', 'CRITICAL')
          GROUP BY service_name
        ),
        span_metrics AS (
          SELECT
            service_name,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as latency_p50,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as latency_p99,
            AVG(duration_ms) as avg_duration,
            MAX(duration_ms) as max_duration,
            SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as span_error_count,
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
          s.service_name,
          COALESCE(m.latency_p50, 0.0) as current_latency_p50,
          COALESCE(m.latency_p95, 0.0) as current_latency_p95,
          COALESCE(m.latency_p99, 0.0) as current_latency_p99,
          COALESCE(m.avg_duration, 0.0) as avg_duration_ms,
          COALESCE(m.max_duration, 0.0) as max_duration_ms,
          COALESCE(m.span_error_count, 0) + COALESCE(l.log_error_count, 0) as error_count,
          COALESCE(m.request_count, 0) as request_count,
          CAST(COALESCE(m.span_error_count, 0) + COALESCE(l.log_error_count, 0) AS FLOAT) / NULLIF(COALESCE(m.request_count, 1), 0) as error_rate,
          COALESCE(m.request_count, 0) / {seconds} as requests_per_second,
          CASE
            WHEN COALESCE(m.span_error_count, 0) + COALESCE(l.log_error_count, 0) > 0 THEN 'critical'
            WHEN m.latency_p50 > COALESCE(b.baseline_latency_p50, m.latency_p50) THEN 'warning'
            WHEN m.request_count / {seconds} > COALESCE(b.baseline_rps, m.request_count / {seconds}) THEN 'warning'
            ELSE 'healthy'
          END as health_status
        FROM all_services s
        LEFT JOIN span_metrics m ON s.service_name = m.service_name
        LEFT JOIN log_error_counts l ON s.service_name = l.service_name
        LEFT JOIN baseline_metrics b ON s.service_name = b.service_name
        ORDER BY COALESCE(m.request_count, 0) DESC, s.service_name
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

    # Convert to PostgreSQL-compatible queries for Lakebase
    current_query = f"""
    WITH service_spans AS (
      SELECT
        (span_value->>'duration_ms')::float as duration_ms,
        (span_value->>'is_error')::boolean as is_error,
        t.trace_start
      FROM {LAKEBASE_SCHEMA_NAME}.traces_assembled_synced t
      CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
      WHERE span_value->>'service_name' = '{service_name}'
        AND t.trace_start >= NOW() - INTERVAL '{interval}'
    )
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
    FROM service_spans
    """

    trends_query = f"""
    WITH service_spans AS (
      SELECT
        (span_value->>'duration_ms')::float as duration_ms,
        (span_value->>'is_error')::boolean as is_error,
        to_timestamp(floor(extract(epoch from t.trace_start) / {bucket_seconds}) * {bucket_seconds}) as time_bucket
      FROM {LAKEBASE_SCHEMA_NAME}.traces_assembled_synced t
      CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
      WHERE span_value->>'service_name' = '{service_name}'
        AND t.trace_start >= NOW() - INTERVAL '{interval}'
    )
    SELECT
      time_bucket as timestamp,
      PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
      AVG(duration_ms) as avg_duration_ms,
      SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
      COUNT(*) as request_count
    FROM service_spans
    GROUP BY time_bucket
    ORDER BY time_bucket
    """

    baseline_query = f"""
    WITH service_spans AS (
      SELECT
        (span_value->>'duration_ms')::float as duration_ms,
        (span_value->>'is_error')::boolean as is_error
      FROM {LAKEBASE_SCHEMA_NAME}.traces_assembled_synced t
      CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
      WHERE span_value->>'service_name' = '{service_name}'
        AND t.trace_start >= NOW() - INTERVAL '{interval}' * 2
        AND t.trace_start < NOW() - INTERVAL '{interval}'
    )
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
    FROM service_spans
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
    service_name: str
):
    from server.models.observability import ServiceDependencies, DependencyInfo

    user_token = request.headers.get("X-Forwarded-Access-Token")
    lakebase_manager = LakebaseManager(user_token=user_token)

    # Convert to PostgreSQL-compatible query for Lakebase
    query = f"""
    WITH current_spans AS (
      SELECT
        span_value->>'service_name' as service_name,
        (span_value->>'duration_ms')::float as duration_ms,
        t.trace_start
      FROM {LAKEBASE_SCHEMA_NAME}.traces_assembled_synced t
      CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
      WHERE t.trace_start >= NOW() - INTERVAL '1 hour'
    ),
    baseline_spans AS (
      SELECT
        span_value->>'service_name' as service_name,
        (span_value->>'duration_ms')::float as duration_ms
      FROM {LAKEBASE_SCHEMA_NAME}.traces_assembled_synced t
      CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
      WHERE t.trace_start >= NOW() - INTERVAL '2 hours'
        AND t.trace_start < NOW() - INTERVAL '1 hour'
    ),
    current_metrics AS (
      SELECT
        service_name,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as latency_p50,
        COUNT(*) as request_count
      FROM current_spans
      GROUP BY service_name
    ),
    baseline_metrics AS (
      SELECT
        service_name,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as baseline_latency_p50,
        COUNT(*) / 3600 as baseline_rps
      FROM baseline_spans
      GROUP BY service_name
    ),
    service_health AS (
      SELECT
        c.service_name,
        CASE
          WHEN c.latency_p50 > COALESCE(b.baseline_latency_p50, c.latency_p50) THEN 'critical'
          WHEN c.request_count / 3600 > COALESCE(b.baseline_rps, c.request_count / 3600) THEN 'warning'
          ELSE 'healthy'
        END as health_status
      FROM current_metrics c
      LEFT JOIN baseline_metrics b ON c.service_name = b.service_name
    ),
    inbound_deps AS (
      SELECT
        d.target_service as service_name,
        d.source_service as related_service,
        d.call_count,
        COALESCE(h.health_status, 'unknown') as health_status
      FROM {LAKEBASE_SCHEMA_NAME}.service_dependencies_synced d
      LEFT JOIN service_health h ON d.source_service = h.service_name
      WHERE d.target_service = '{service_name}'
    ),
    outbound_deps AS (
      SELECT
        d.source_service as service_name,
        d.target_service as related_service,
        d.call_count,
        COALESCE(h.health_status, 'unknown') as health_status
      FROM {LAKEBASE_SCHEMA_NAME}.service_dependencies_synced d
      LEFT JOIN service_health h ON d.target_service = h.service_name
      WHERE d.source_service = '{service_name}'
    )
    SELECT
      'inbound' as direction,
      related_service as service_name,
      call_count,
      health_status
    FROM inbound_deps
    UNION ALL
    SELECT
      'outbound' as direction,
      related_service as service_name,
      call_count,
      health_status
    FROM outbound_deps
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

    # Convert to PostgreSQL-compatible query for Lakebase
    # Use JSONB containment operator to check if service is in services_involved array
    query = f"""
    SELECT
      trace_id,
      trace_start,
      services_involved,
      total_trace_duration_ms as total_duration_ms,
      span_count
    FROM {LAKEBASE_SCHEMA_NAME}.traces_assembled_synced
    WHERE services_involved::jsonb @> '"{service_name}"'::jsonb
      AND trace_start >= NOW() - INTERVAL '{interval}'
    ORDER BY trace_start DESC
    LIMIT 100
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

    # Convert to PostgreSQL-compatible queries for Lakebase
    trace_query = f"""
    SELECT
      trace_id,
      trace_start
    FROM {LAKEBASE_SCHEMA_NAME}.traces_assembled_synced
    WHERE trace_id = '{trace_id}'
    LIMIT 1
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
