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
    WITH current_spans AS (
      SELECT 
        span.service_name,
        span.duration_ms,
        span.is_error,
        t.trace_start
      FROM jmr_demo.zerobus.traces_assembled_silver t
      LATERAL VIEW explode(span_details) AS span
      WHERE t.trace_start >= NOW() - INTERVAL {interval}
    ),
    baseline_spans AS (
      SELECT 
        span.service_name,
        span.duration_ms
      FROM jmr_demo.zerobus.traces_assembled_silver t
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
    request: Request,
    service_name: str,
    time_range: TimeRange = Query(default="1h", description="Time range for metrics")
) -> ServiceMetricsDetail:
    user_token = request.headers.get("X-Forwarded-Access-Token")
    warehouse_manager = WarehouseManager(user_token=user_token)
    interval, seconds = get_time_range_interval(time_range)
    
    current_query = f"""
    WITH service_spans AS (
      SELECT 
        span.duration_ms,
        span.is_error,
        t.trace_start
      FROM jmr_demo.zerobus.traces_assembled_silver t
      LATERAL VIEW explode(span_details) AS span
      WHERE span.service_name = '{service_name}'
        AND t.trace_start >= NOW() - INTERVAL {interval}
    )
    SELECT
      PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as latency_p50,
      PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
      PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as latency_p99,
      AVG(duration_ms) as avg_duration_ms,
      MAX(duration_ms) as max_duration_ms,
      SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
      CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) as error_rate,
      COUNT(*) as request_count,
      COUNT(*) / {seconds} as requests_per_second
    FROM service_spans
    """
    
    trends_query = f"""
    WITH service_spans AS (
      SELECT 
        span.duration_ms,
        span.is_error,
        date_trunc('minute', t.trace_start) as time_bucket
      FROM jmr_demo.zerobus.traces_assembled_silver t
      LATERAL VIEW explode(span_details) AS span
      WHERE span.service_name = '{service_name}'
        AND t.trace_start >= NOW() - INTERVAL {interval}
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
        span.duration_ms,
        span.is_error
      FROM jmr_demo.zerobus.traces_assembled_silver t
      LATERAL VIEW explode(span_details) AS span
      WHERE span.service_name = '{service_name}'
        AND t.trace_start >= NOW() - INTERVAL {interval} * 2
        AND t.trace_start < NOW() - INTERVAL {interval}
    )
    SELECT
      PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as latency_p50,
      PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
      PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as latency_p99,
      AVG(duration_ms) as avg_duration_ms,
      MAX(duration_ms) as max_duration_ms,
      SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
      CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) as error_rate,
      COUNT(*) as request_count,
      COUNT(*) / {seconds} as requests_per_second
    FROM service_spans
    """
    
    try:
        from server.models.observability import MetricsSnapshot, MetricsTimeSeries
        
        current_results = warehouse_manager.execute_query(current_query)
        trends_results = warehouse_manager.execute_query(trends_query)
        baseline_results = warehouse_manager.execute_query(baseline_query)
        
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
    warehouse_manager = WarehouseManager(user_token=user_token)
    
    query = f"""
    WITH current_spans AS (
      SELECT 
        span.service_name,
        span.duration_ms,
        t.trace_start
      FROM jmr_demo.zerobus.traces_assembled_silver t
      LATERAL VIEW explode(span_details) AS span
      WHERE t.trace_start >= NOW() - INTERVAL 1 HOUR
    ),
    baseline_spans AS (
      SELECT 
        span.service_name,
        span.duration_ms
      FROM jmr_demo.zerobus.traces_assembled_silver t
      LATERAL VIEW explode(span_details) AS span
      WHERE t.trace_start >= NOW() - INTERVAL 2 HOUR
        AND t.trace_start < NOW() - INTERVAL 1 HOUR
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
      FROM jmr_demo.zerobus.service_dependencies d
      LEFT JOIN service_health h ON d.source_service = h.service_name
      WHERE d.target_service = '{service_name}'
    ),
    outbound_deps AS (
      SELECT 
        d.source_service as service_name,
        d.target_service as related_service,
        d.call_count,
        COALESCE(h.health_status, 'unknown') as health_status
      FROM jmr_demo.zerobus.service_dependencies d
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
        results = warehouse_manager.execute_query(query)
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
    warehouse_manager = WarehouseManager(user_token=user_token)
    interval, seconds = get_time_range_interval(time_range)
    
    query = f"""
    SELECT 
      trace_id,
      trace_start,
      services_involved,
      total_trace_duration_ms as total_duration_ms,
      span_count
    FROM jmr_demo.zerobus.traces_assembled_silver
    WHERE array_contains(services_involved, '{service_name}')
      AND trace_start >= NOW() - INTERVAL {interval}
    ORDER BY trace_start DESC
    LIMIT 100
    """
    
    try:
        results = warehouse_manager.execute_query(query)
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
    warehouse_manager = WarehouseManager(user_token=user_token)
    
    trace_query = f"""
    SELECT 
      trace_id,
      trace_start
    FROM jmr_demo.zerobus.traces_assembled_silver
    WHERE trace_id = '{trace_id}'
    LIMIT 1
    """
    
    spans_query = f"""
    SELECT 
      service_name,
      SUM(duration_ms) as total_duration_ms
    FROM jmr_demo.zerobus.traces_silver
    WHERE trace_id = '{trace_id}'
    GROUP BY service_name
    ORDER BY total_duration_ms DESC
    """
    
    try:
        trace_results = warehouse_manager.execute_query(trace_query)
        if not trace_results:
            raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")
        
        spans_results = warehouse_manager.execute_query(spans_query)
        
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
