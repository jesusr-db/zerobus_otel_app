from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal
from server.models.observability import DependencyGraph, GraphNode, GraphEdge
from server.services.warehouse_manager import WarehouseManager

router = APIRouter()

TimeRange = Literal["1h", "24h"]


def get_time_range_interval(time_range: TimeRange) -> tuple[str, int]:
    intervals = {
        "1h": ("1 HOUR", 3600),
        "24h": ("24 HOUR", 86400),
    }
    return intervals[time_range]


@router.get("/graph")
async def get_dependency_graph(
    request: Request,
    time_range: TimeRange = Query(default="1h", description="Time range for health metrics")
) -> DependencyGraph:
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
        SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
        COUNT(*) as request_count,
        CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) as error_rate
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
    ),
    service_health AS (
      SELECT
        c.service_name,
        c.error_count,
        c.request_count,
        c.error_rate,
        CASE 
          WHEN c.latency_p50 > COALESCE(b.baseline_latency_p50, c.latency_p50) THEN 'critical'
          WHEN c.request_count / {seconds} > COALESCE(b.baseline_rps, c.request_count / {seconds}) THEN 'warning'
          ELSE 'healthy'
        END as health_status
      FROM current_metrics c
      LEFT JOIN baseline_metrics b ON c.service_name = b.service_name
    ),
    all_services AS (
      SELECT DISTINCT source_service as service_name FROM jmr_demo.zerobus.service_dependencies
      UNION
      SELECT DISTINCT target_service as service_name FROM jmr_demo.zerobus.service_dependencies
    )
    SELECT 
      'node' as row_type,
      s.service_name as id,
      COALESCE(h.health_status, 'healthy') as health,
      COALESCE(h.error_rate, 0.0) as errorRate,
      COALESCE(h.request_count, 0) as requestCount,
      NULL as source,
      NULL as target,
      NULL as callCount
    FROM all_services s
    LEFT JOIN service_health h ON s.service_name = h.service_name
    
    UNION ALL
    
    SELECT 
      'edge' as row_type,
      NULL as id,
      NULL as health,
      NULL as errorRate,
      NULL as requestCount,
      d.source_service as source,
      d.target_service as target,
      d.call_count as callCount
    FROM jmr_demo.zerobus.service_dependencies d
    """
    
    try:
        results = warehouse_manager.execute_query(query)
        
        nodes = []
        edges = []
        
        for row in results:
            if row.get('row_type') == 'node':
                nodes.append(GraphNode(
                    id=row['id'],
                    health=row['health'],
                    errorRate=float(row['errorRate']),
                    requestCount=int(row['requestCount'])
                ))
            elif row.get('row_type') == 'edge':
                edges.append(GraphEdge(
                    source=row['source'],
                    target=row['target'],
                    callCount=int(row['callCount'])
                ))
        
        return DependencyGraph(nodes=nodes, edges=edges)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
