from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal
from server.models.observability import DependencyGraph, GraphNode, GraphEdge
from server.services.warehouse_manager import WarehouseManager

router = APIRouter()

TimeRange = Literal["15m", "1h", "24h"]


def get_time_range_interval(time_range: TimeRange) -> tuple[str, int]:
    intervals = {
        "15m": ("15 MINUTE", 900),
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
    WITH service_spans AS (
      SELECT 
        span.service_name,
        span.is_error,
        t.trace_start
      FROM jmr_demo.zerobus.traces_assembled_silver t
      LATERAL VIEW explode(span_details) AS span
      WHERE t.trace_start >= NOW() - INTERVAL {interval}
    ),
    service_health AS (
      SELECT
        service_name,
        SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
        COUNT(*) as request_count,
        CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) as error_rate,
        CASE 
          WHEN CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) > 0.05 THEN 'critical'
          WHEN CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) > 0.01 THEN 'warning'
          ELSE 'healthy'
        END as health_status
      FROM service_spans
      GROUP BY service_name
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
