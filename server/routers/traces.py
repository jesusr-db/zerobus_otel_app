from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal
import logging
from server.models.observability import TraceInfo, TraceWaterfall, SpanWaterfall
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


@router.get("")
async def get_all_traces(
    request: Request,
    time_range: TimeRange = Query(default="1h", description="Time range for traces")
):
    user_token = request.headers.get("X-Forwarded-Access-Token")
    interval, seconds = get_time_range_interval(time_range)

    # Use Lakebase (PostgreSQL) backend only
    # Optimized query - aggregate directly without CTE overhead
    data_manager = LakebaseManager(user_token=user_token)
    query = f"""
    SELECT
      trace_id,
      MIN(start_timestamp) as trace_start,
      ARRAY_AGG(DISTINCT service_name) as services_involved,
      COUNT(*) as span_count,
      SUM(duration_ms) as total_duration_ms
    FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
    WHERE start_timestamp >= NOW() - INTERVAL '{interval}'
      AND trace_id IS NOT NULL
    GROUP BY trace_id
    ORDER BY trace_start DESC
    LIMIT 100
    """

    try:
        results = data_manager.execute_query(query)
        if not results:
            logger.info("No traces found")
            return []

        traces = []
        for row in results:
            total_duration = float(row.get('total_duration_ms') or 0)

            # Create TraceInfo with calculated duration
            trace_data = {
                'trace_id': row['trace_id'],
                'trace_start': row['trace_start'],
                'services_involved': row['services_involved'],
                'total_duration_ms': total_duration,
                'span_count': row['span_count']
            }
            traces.append(TraceInfo(**trace_data))

        return traces
    except Exception as e:
        logger.error(f"Traces query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/waterfall/{trace_id}")
async def get_trace_waterfall(
    request: Request,
    trace_id: str
) -> TraceWaterfall:
    user_token = request.headers.get("X-Forwarded-Access-Token")

    # Use Lakebase (PostgreSQL) backend only - query traces_silver_synced directly
    data_manager = LakebaseManager(user_token=user_token)
    spans_query = f"""
    SELECT
      trace_id,
      span_id,
      name,
      service_name,
      parent_span_id,
      start_timestamp,
      duration_ms,
      is_error,
      attributes
    FROM {LAKEBASE_SCHEMA_NAME}.traces_silver_synced
    WHERE trace_id = '{trace_id}'
    ORDER BY start_timestamp
    """

    try:
        logger.info(f"Fetching waterfall for trace: {trace_id}")
        spans_results = data_manager.execute_query(spans_query)

        if not spans_results:
            logger.warning(f"Trace not found: {trace_id}")
            raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")

        logger.info(f"Retrieved {len(spans_results)} spans for trace {trace_id}")

        # Calculate trace timing from spans using start_timestamp
        trace_start = min(s['start_timestamp'] for s in spans_results)

        # Calculate start offsets relative to trace start (in milliseconds)
        spans = []
        max_end_ms = 0.0
        for span in spans_results:
            # Calculate offset from trace start in milliseconds
            span_start = span['start_timestamp']
            start_offset_ms = (span_start - trace_start).total_seconds() * 1000.0
            duration_ms = float(span.get('duration_ms') or 0)

            # Track max end time for total duration
            end_ms = start_offset_ms + duration_ms
            max_end_ms = max(max_end_ms, end_ms)

            # Check for errors from is_error column or attributes
            is_error = span.get('is_error', False)
            if not is_error:
                attributes = span.get('attributes', {})
                if isinstance(attributes, dict):
                    status_code = attributes.get('http.status_code')
                    if status_code:
                        try:
                            is_error = int(status_code) >= 400
                        except (ValueError, TypeError):
                            pass

            spans.append(SpanWaterfall(
                span_id=span['span_id'],
                name=span['name'],
                service_name=span['service_name'],
                duration_ms=duration_ms,
                start_offset_ms=start_offset_ms,
                parent_span_id=span.get('parent_span_id'),
                is_error=is_error
            ))

        total_duration_ms = max_end_ms if max_end_ms > 0 else sum(s.duration_ms for s in spans)
        logger.info(f"Trace {trace_id}: duration={total_duration_ms}ms, spans={len(spans)}")

        return TraceWaterfall(
            trace_id=trace_id,
            trace_start=trace_start,
            total_duration_ms=total_duration_ms,
            spans=spans
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Waterfall query failed for {trace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
