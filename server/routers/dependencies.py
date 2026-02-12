from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal
import logging
from server.models.observability import DependencyGraph, GraphNode, GraphEdge
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


@router.get("/graph")
async def get_dependency_graph(
    request: Request,
    time_range: TimeRange = Query(default="1h", description="Time range for health metrics")
) -> DependencyGraph:
    user_token = request.headers.get("X-Forwarded-Access-Token")
    interval, seconds = get_time_range_interval(time_range)

    # Use Lakebase (PostgreSQL) backend only
    # Optimized query - single scan for service health
    data_manager = LakebaseManager(user_token=user_token)
    query = f"""
    WITH service_health AS (
      SELECT
        service_name,
        SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
        COUNT(*) as request_count,
        CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) as error_rate,
        CASE
          WHEN SUM(CASE WHEN is_error THEN 1 ELSE 0 END) > 0 THEN 'critical'
          ELSE 'healthy'
        END as health_status
      FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
      WHERE start_timestamp >= NOW() - INTERVAL '{interval}'
        AND service_name IS NOT NULL
      GROUP BY service_name
    ),
    recent_dependencies AS (
      SELECT source_service, target_service, call_count
      FROM {LAKEBASE_SCHEMA_NAME}.service_dependencies_synced
      WHERE last_seen >= NOW() - INTERVAL '{interval}'
    ),
    all_services AS (
      SELECT DISTINCT source_service as service_name FROM recent_dependencies
      UNION
      SELECT DISTINCT target_service as service_name FROM recent_dependencies
    )
    SELECT
      'node' as row_type,
      s.service_name as id,
      COALESCE(h.health_status, 'healthy') as health,
      COALESCE(h.error_rate, 0.0) as "errorRate",
      COALESCE(h.request_count, 0) as "requestCount",
      NULL as source,
      NULL as target,
      NULL as "callCount"
    FROM all_services s
    LEFT JOIN service_health h ON s.service_name = h.service_name

    UNION ALL

    SELECT
      'edge' as row_type,
      NULL as id,
      NULL as health,
      NULL as "errorRate",
      NULL as "requestCount",
      d.source_service as source,
      d.target_service as target,
      d.call_count as "callCount"
    FROM recent_dependencies d
    """
    
    try:
        results = data_manager.execute_query(query)
        
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
