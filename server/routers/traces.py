from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal
import logging
from server.models.observability import TraceInfo
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


@router.get("")
async def get_all_traces(
    request: Request,
    time_range: TimeRange = Query(default="1h", description="Time range for traces")
):
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
    FROM {OBSERVABILITY_TABLE_PREFIX}.traces_assembled_silver
    WHERE trace_start >= NOW() - INTERVAL {interval}
    ORDER BY trace_start DESC
    LIMIT 100
    """
    
    try:
        results = warehouse_manager.execute_query(query)
        if not results:
            logger.info("No traces found")
            return []
        
        return [TraceInfo(**row) for row in results]
    except Exception as e:
        logger.error(f"Traces query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
