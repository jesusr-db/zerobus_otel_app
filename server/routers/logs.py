"""Logs API router for log analysis and troubleshooting."""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal, Optional, List
import logging
import json
import re
from server.models.logs import LogEntry, LogsResponse, SeverityTimelineResponse, SeverityTimelinePoint
from server.services.lakebase_manager import LakebaseManager
from server.config import LAKEBASE_SCHEMA_NAME

logger = logging.getLogger(__name__)
router = APIRouter()

TimeRange = Literal["5m", "1h", "1d", "1w"]
SearchMode = Literal["simple", "advanced"]


def get_time_range_interval(time_range: TimeRange) -> tuple[str, int]:
    """
    Convert time range to SQL interval string and seconds.

    Note: PostgreSQL requires lowercase with plural forms for quantities > 1
    """
    intervals = {
        "5m": ("5 minutes", 300),
        "1h": ("1 hour", 3600),
        "1d": ("1 day", 86400),
        "1w": ("7 days", 604800),
    }
    return intervals[time_range]


def get_timeline_granularity(time_range: TimeRange) -> int:
    """Get appropriate time bucket granularity in seconds based on time range."""
    granularities = {
        "5m": 30,      # 30-second buckets for 5 minutes
        "1h": 300,     # 5-minute (300 seconds) buckets for 1 hour
        "1d": 3600,    # 1-hour (3600 seconds) buckets for 1 day
        "1w": 86400,   # 1-day (86400 seconds) buckets for 1 week
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
    service_name: Optional[str] = Query(None, description="Service name to filter logs (optional, searches all if not specified)"),
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
    lakebase = LakebaseManager(user_token=user_token)
    interval, seconds = get_time_range_interval(time_range)

    try:
        # Build WHERE clause components
        where_clauses = [
            f"log_timestamp >= NOW() - INTERVAL '{interval}'"
        ]
        params = []

        # Add service filter if specified
        if service_name:
            where_clauses.append("service_name = %s")
            params.append(service_name)

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
        FROM {LAKEBASE_SCHEMA_NAME}.logs_synced
        WHERE {where_sql}
        """

        count_result = lakebase.execute_query(count_query, params)
        total_count = count_result[0]['total'] if count_result else 0

        # Get severity counts
        severity_query = f"""
        SELECT
            severity_text,
            COUNT(*) as count
        FROM {LAKEBASE_SCHEMA_NAME}.logs_synced
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
        FROM {LAKEBASE_SCHEMA_NAME}.logs_synced
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
    service_name: Optional[str] = Query(None, description="Service name to filter logs (optional, all services if not specified)"),
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
    lakebase = LakebaseManager(user_token=user_token)
    interval, seconds = get_time_range_interval(time_range)
    granularity = get_timeline_granularity(time_range)

    try:
        # Build WHERE clause
        where_conditions = [f"log_timestamp >= NOW() - INTERVAL '{interval}'"]
        params = []

        if service_name:
            where_conditions.append("service_name = %s")
            params.append(service_name)

        where_clause = " AND ".join(where_conditions)

        # Use epoch-based bucketing for arbitrary time intervals
        # FLOOR(EXTRACT(EPOCH FROM timestamp) / bucket_seconds) gives us the bucket number
        # Multiply back and convert to timestamp to get the bucket start time
        query = f"""
        SELECT
            TO_TIMESTAMP(FLOOR(EXTRACT(EPOCH FROM log_timestamp) / {granularity}) * {granularity}) as bucket,
            COUNT(*) FILTER (WHERE severity_text = 'ERROR') as ERROR,
            COUNT(*) FILTER (WHERE severity_text = 'WARN') as WARN,
            COUNT(*) FILTER (WHERE severity_text = 'INFO') as INFO,
            COUNT(*) FILTER (WHERE severity_text = 'DEBUG') as DEBUG
        FROM {LAKEBASE_SCHEMA_NAME}.logs_synced
        WHERE {where_clause}
        GROUP BY bucket
        ORDER BY bucket ASC
        """

        results = lakebase.execute_query(query, params)

        timeline = []
        for row in results:
            point = SeverityTimelinePoint(
                timestamp=row['bucket'],
                ERROR=row['error'] or 0,
                WARN=row['warn'] or 0,
                INFO=row['info'] or 0,
                DEBUG=row['debug'] or 0
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
