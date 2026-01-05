from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal
import logging
from server.models.observability import TraceInfo, TraceWaterfall, SpanWaterfall
from server.services.warehouse_manager import WarehouseManager
from server.services.lakebase_manager import LakebaseManager
from server.config import OBSERVABILITY_TABLE_PREFIX, DATA_BACKEND

logger = logging.getLogger(__name__)
router = APIRouter()

TimeRange = Literal["5m", "1h", "1d", "1w"]


def get_time_range_interval(time_range: TimeRange) -> tuple[str, int]:
    """
    Convert time range to SQL interval string and seconds.
    Returns (interval_string, seconds)
    """
    intervals = {
        "5m": ("5 MINUTE", 300),
        "1h": ("1 HOUR", 3600),
        "1d": ("1 DAY", 86400),
        "1w": ("7 DAY", 604800),
    }
    return intervals[time_range]


@router.get("")
async def get_all_traces(
    request: Request,
    time_range: TimeRange = Query(default="1h", description="Time range for traces")
):
    user_token = request.headers.get("X-Forwarded-Access-Token")
    interval, seconds = get_time_range_interval(time_range)
    
    if DATA_BACKEND == "lakebase":
        data_manager = LakebaseManager(user_token=user_token)
        query = f"""
        SELECT 
          trace_id,
          trace_start,
          services_involved,
          total_trace_duration_ms as total_duration_ms,
          span_count
        FROM zerobus_sdp.traces_assembled_synced
        WHERE trace_start >= NOW() - INTERVAL '{interval}'
        ORDER BY trace_start DESC
        LIMIT 100
        """
    else:
        data_manager = WarehouseManager(user_token=user_token)
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
        results = data_manager.execute_query(query)
        if not results:
            logger.info("No traces found")
            return []
        
        return [TraceInfo(**row) for row in results]
    except Exception as e:
        logger.error(f"Traces query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/waterfall/{trace_id}")
async def get_trace_waterfall(
    request: Request,
    trace_id: str
) -> TraceWaterfall:
    user_token = request.headers.get("X-Forwarded-Access-Token")
    
    if DATA_BACKEND == "lakebase":
        data_manager = LakebaseManager(user_token=user_token)
        assembled_query = f"""
        SELECT 
          trace_id,
          trace_start,
          total_trace_duration_ms,
          span_details
        FROM zerobus_sdp.traces_assembled_synced
        WHERE trace_id = '{trace_id}'
        LIMIT 1
        """
        
        spans_query = f"""
        SELECT *
        FROM zerobus_sdp.traces_silver_synced
        WHERE trace_id = '{trace_id}'
        LIMIT 1
        """
    else:
        data_manager = WarehouseManager(user_token=user_token)
        assembled_query = f"""
        SELECT 
          trace_id,
          trace_start,
          total_trace_duration_ms,
          span_details
        FROM {OBSERVABILITY_TABLE_PREFIX}.traces_assembled_silver
        WHERE trace_id = '{trace_id}'
        LIMIT 1
        """
        
        spans_query = f"""
        SELECT 
          span_id,
          parent_span_id,
          name,
          service_name,
          start_time_unix_nano,
          end_time_unix_nano,
          attributes
        FROM {OBSERVABILITY_TABLE_PREFIX}.traces_silver
        WHERE trace_id = '{trace_id}'
        ORDER BY start_time_unix_nano ASC
        """
    
    try:
        logger.info(f"Fetching waterfall for trace: {trace_id}")
        assembled_results = data_manager.execute_query(assembled_query)
        if not assembled_results:
            logger.warning(f"Trace not found: {trace_id}")
            raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")
        
        trace_data = assembled_results[0]
        logger.info(f"Trace found: {trace_data.get('trace_id')}, querying spans...")
        
        try:
            spans_results = data_manager.execute_query(spans_query)
            logger.info(f"Retrieved {len(spans_results) if spans_results else 0} spans")
            if spans_results and len(spans_results) > 0:
                logger.info(f"Available columns in traces_silver_synced: {list(spans_results[0].keys())}")
        except Exception as span_query_error:
            logger.error(f"Span query failed, falling back to span_details: {span_query_error}")
            spans_results = None
        
        if spans_results and len(spans_results) > 0 and 'start_time_unix_nano' in spans_results[0]:
            # Use detailed span timing data
            trace_start_nano = min(s['start_time_unix_nano'] for s in spans_results)
            
            spans = []
            for span in spans_results:
                start_offset_ns = span['start_time_unix_nano'] - trace_start_nano
                duration_ns = span['end_time_unix_nano'] - span['start_time_unix_nano']
                
                attributes = span.get('attributes', {})
                is_error = False
                if isinstance(attributes, dict):
                    status_code = attributes.get('http.status_code')
                    is_error = status_code and int(status_code) >= 400
                
                spans.append(SpanWaterfall(
                    span_id=span['span_id'],
                    name=span['name'],
                    service_name=span['service_name'],
                    duration_ms=duration_ns / 1_000_000,
                    start_offset_ms=start_offset_ns / 1_000_000,
                    parent_span_id=span.get('parent_span_id'),
                    is_error=is_error
                ))
        else:
            spans = []
            for span in trace_data['span_details']:
                spans.append(SpanWaterfall(
                    span_id=span.get('span_id', ''),
                    name=span.get('name', ''),
                    service_name=span.get('service_name', ''),
                    duration_ms=float(span.get('duration_ms', 0)),
                    start_offset_ms=0.0,
                    parent_span_id=span.get('parent_span_id'),
                    is_error=span.get('is_error', False)
                ))
        
        return TraceWaterfall(
            trace_id=trace_data['trace_id'],
            trace_start=trace_data['trace_start'],
            total_duration_ms=float(trace_data['total_trace_duration_ms']),
            spans=spans
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Waterfall query failed for {trace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
