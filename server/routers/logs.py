"""Logs API router for log analysis and troubleshooting."""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal, Optional, List
import logging
import json
import re
from server.models.logs import LogEntry, LogsResponse, SeverityTimelineResponse, SeverityTimelinePoint
from server.services.lakebase_manager import LakebaseManager
from server.config import DATA_BACKEND

logger = logging.getLogger(__name__)
router = APIRouter()

TimeRange = Literal["5m", "1h", "1d", "1w"]
SearchMode = Literal["simple", "advanced"]


def get_time_range_interval(time_range: TimeRange) -> tuple[str, int]:
    """Convert time range to SQL interval string and seconds."""
    intervals = {
        "5m": ("5 MINUTE", 300),
        "1h": ("1 HOUR", 3600),
        "1d": ("1 DAY", 86400),
        "1w": ("7 DAY", 604800),
    }
    return intervals[time_range]


def get_timeline_granularity(time_range: TimeRange) -> str:
    """Get appropriate time bucket granularity based on time range."""
    granularities = {
        "5m": "30 seconds",   # 30-second buckets for 5 minutes
        "1h": "5 minutes",    # 5-minute buckets for 1 hour
        "1d": "1 hour",       # 1-hour buckets for 1 day
        "1w": "1 day",        # 1-day buckets for 1 week
    }
    return granularities[time_range]


def parse_advanced_search(search: str) -> dict:
    """
    Parse advanced search syntax into SQL conditions.

    Syntax examples:
    - body:database - Search only body field
    - severity:ERROR - Filter by severity
    - trace_id:abc123 - Filter by trace ID
    - attributes.error.type:ConnectionError - Search in attributes
    - Combined: severity:ERROR AND body:database

    Returns dict with field-specific conditions.
    """
    conditions = {
        "body": [],
        "severity": [],
        "trace_id": [],
        "attributes": []
    }

    # Parse field:value patterns
    # Pattern: field:value or field:"multi word value"
    pattern = r'(\w+(?:\.\w+)*):(?:"([^"]+)"|(\S+))'
    matches = re.findall(pattern, search)

    for match in matches:
        field_path = match[0]
        value = match[1] if match[1] else match[2]

        # Map field paths to SQL conditions
        if field_path == "body":
            conditions["body"].append(value)
        elif field_path == "severity":
            conditions["severity"].append(value.upper())
        elif field_path == "trace_id":
            conditions["trace_id"].append(value)
        elif field_path.startswith("attributes."):
            # Extract attribute key path
            attr_key = field_path.replace("attributes.", "")
            conditions["attributes"].append((attr_key, value))

    return conditions


def build_search_clause(search: str, search_mode: SearchMode) -> tuple[str, List[str]]:
    """
    Build SQL WHERE clause for search.

    Returns (sql_clause, parameters_list).
    """
    if not search:
        return ("", [])

    if search_mode == "simple":
        # Simple search: body OR attributes (cast attributes to text for ILIKE)
        clause = "(body ILIKE %s OR attributes::text ILIKE %s)"
        search_pattern = f"%{search}%"
        return (clause, [search_pattern, search_pattern])

    else:  # advanced
        conditions_dict = parse_advanced_search(search)
        clauses = []
        params = []

        # Body search
        if conditions_dict["body"]:
            body_clauses = []
            for term in conditions_dict["body"]:
                body_clauses.append("body ILIKE %s")
                params.append(f"%{term}%")
            if body_clauses:
                clauses.append(f"({' OR '.join(body_clauses)})")

        # Severity filter
        if conditions_dict["severity"]:
            severity_placeholders = ', '.join(['%s'] * len(conditions_dict["severity"]))
            clauses.append(f"severity_text IN ({severity_placeholders})")
            params.extend(conditions_dict["severity"])

        # Trace ID filter
        if conditions_dict["trace_id"]:
            trace_clauses = []
            for trace in conditions_dict["trace_id"]:
                trace_clauses.append("trace_id = %s")
                params.append(trace)
            if trace_clauses:
                clauses.append(f"({' OR '.join(trace_clauses)})")

        # Attributes search
        if conditions_dict["attributes"]:
            attr_clauses = []
            for attr_key, attr_value in conditions_dict["attributes"]:
                # Search in JSON string for the key-value pair (cast to text for ILIKE)
                attr_clauses.append("attributes::text ILIKE %s")
                params.append(f'%"{attr_key}"%{attr_value}%')
            if attr_clauses:
                clauses.append(f"({' OR '.join(attr_clauses)})")

        if clauses:
            # Use AND to combine all conditions
            return (" AND ".join(clauses), params)
        else:
            return ("", [])


@router.get("/list")
async def get_logs(
    request: Request,
    service_name: str = Query(..., description="Service name to filter logs"),
    time_range: TimeRange = Query(default="1h", description="Time range for logs"),
    search: Optional[str] = Query(None, description="Search term for body and attributes"),
    search_mode: SearchMode = Query(default="simple", description="Search mode: simple or advanced"),
    severity_filter: Optional[str] = Query(None, description="Comma-separated severity levels (ERROR,WARN,INFO,DEBUG)"),
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=100, ge=1, le=500, description="Logs per page (max 500)")
) -> LogsResponse:
    """
    List logs with filtering and pagination.

    Supports:
    - Service filtering (required)
    - Time range filtering
    - Simple search (searches body and attributes)
    - Advanced search (field-specific: body:term, severity:ERROR, etc.)
    - Severity multi-select filtering
    - Trace ID filtering
    - Pagination
    """
    user_token = request.headers.get("X-Forwarded-Access-Token")

    if DATA_BACKEND != "lakebase":
        raise HTTPException(status_code=501, detail="Logs only supported with Lakebase backend")

    lakebase = LakebaseManager(user_token=user_token)
    interval, seconds = get_time_range_interval(time_range)

    try:
        # Build WHERE clause components
        where_clauses = [
            "service_name = %s",
            f"log_timestamp >= NOW() - INTERVAL '{interval}'"
        ]
        params = [service_name]

        # Add search clause
        if search:
            search_clause, search_params = build_search_clause(search, search_mode)
            if search_clause:
                where_clauses.append(f"({search_clause})")
                params.extend(search_params)

        # Add severity filter
        if severity_filter:
            severities = [s.strip().upper() for s in severity_filter.split(",")]
            severity_placeholders = ', '.join(['%s'] * len(severities))
            where_clauses.append(f"severity_text IN ({severity_placeholders})")
            params.extend(severities)

        # Add trace ID filter
        if trace_id:
            where_clauses.append("trace_id = %s")
            params.append(trace_id)

        # Build complete WHERE clause
        where_sql = " AND ".join(where_clauses)

        # Calculate offset
        offset = (page - 1) * page_size

        # Get total count
        count_query = f"""
        SELECT COUNT(*) as total
        FROM zerobus_sdp.logs_synced
        WHERE {where_sql}
        """

        count_result = lakebase.execute_query(count_query, params)
        total_count = count_result[0]['total'] if count_result else 0

        # Get severity counts
        severity_query = f"""
        SELECT
            severity_text,
            COUNT(*) as count
        FROM zerobus_sdp.logs_synced
        WHERE {where_sql}
        GROUP BY severity_text
        """

        severity_results = lakebase.execute_query(severity_query, params)
        # Filter out None severity_text values
        severity_counts = {
            row['severity_text']: row['count']
            for row in severity_results
            if row['severity_text'] is not None
        }

        # Get paginated logs
        logs_query = f"""
        SELECT
            event_name,
            trace_id,
            span_id,
            log_timestamp,
            observed_timestamp,
            severity_text,
            body,
            service_name,
            attributes
        FROM zerobus_sdp.logs_synced
        WHERE {where_sql}
        ORDER BY log_timestamp DESC
        LIMIT %s OFFSET %s
        """

        logs_params = params + [page_size, offset]
        logs_results = lakebase.execute_query(logs_query, logs_params)

        # Parse logs and handle attributes JSON
        logs = []
        for row in logs_results:
            # Handle attributes - could be dict (already parsed) or string (needs parsing)
            attributes = {}
            if row['attributes']:
                if isinstance(row['attributes'], dict):
                    # Already parsed by SQLAlchemy/PostgreSQL
                    attributes = row['attributes']
                elif isinstance(row['attributes'], str):
                    # Need to parse JSON string
                    try:
                        attributes = json.loads(row['attributes'])
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse attributes JSON for log: {row.get('event_name')}")
                        attributes = {}
                else:
                    logger.warning(f"Unexpected attributes type: {type(row['attributes'])}")
                    attributes = {}

            log_entry = LogEntry(
                event_name=row['event_name'],
                trace_id=row['trace_id'],
                span_id=row['span_id'],
                log_timestamp=row['log_timestamp'],
                observed_timestamp=row['observed_timestamp'],
                severity_text=row['severity_text'],
                body=row['body'],
                service_name=row['service_name'],
                attributes=attributes
            )
            logs.append(log_entry)

        # Calculate if there are more pages
        has_more = (offset + page_size) < total_count

        return LogsResponse(
            logs=logs,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=has_more,
            severity_counts=severity_counts
        )

    except Exception as e:
        logger.error(f"Logs query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/severity-timeline")
async def get_severity_timeline(
    request: Request,
    service_name: str = Query(..., description="Service name to filter logs"),
    time_range: TimeRange = Query(default="1h", description="Time range for timeline")
) -> SeverityTimelineResponse:
    """
    Get severity distribution over time for visualization.

    Returns bucketed counts by severity with auto-adjusted granularity:
    - 5m range → 30-second buckets
    - 1h range → 5-minute buckets
    - 1d range → 1-hour buckets
    - 1w range → 1-day buckets
    """
    user_token = request.headers.get("X-Forwarded-Access-Token")

    if DATA_BACKEND != "lakebase":
        raise HTTPException(status_code=501, detail="Logs only supported with Lakebase backend")

    lakebase = LakebaseManager(user_token=user_token)
    interval, seconds = get_time_range_interval(time_range)
    granularity = get_timeline_granularity(time_range)

    try:
        query = f"""
        SELECT
            DATE_TRUNC('{granularity}', log_timestamp) as bucket,
            COUNT(*) FILTER (WHERE severity_text = 'ERROR') as ERROR,
            COUNT(*) FILTER (WHERE severity_text = 'WARN') as WARN,
            COUNT(*) FILTER (WHERE severity_text = 'INFO') as INFO,
            COUNT(*) FILTER (WHERE severity_text = 'DEBUG') as DEBUG
        FROM zerobus_sdp.logs_synced
        WHERE service_name = %s
            AND log_timestamp >= NOW() - INTERVAL '{interval}'
        GROUP BY bucket
        ORDER BY bucket ASC
        """

        results = lakebase.execute_query(query, [service_name])

        timeline = []
        for row in results:
            point = SeverityTimelinePoint(
                timestamp=row['bucket'],
                ERROR=row['ERROR'] or 0,
                WARN=row['WARN'] or 0,
                INFO=row['INFO'] or 0,
                DEBUG=row['DEBUG'] or 0
            )
            timeline.append(point)

        return SeverityTimelineResponse(
            timeline=timeline,
            service_name=service_name,
            time_range=time_range
        )

    except Exception as e:
        logger.error(f"Severity timeline query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
