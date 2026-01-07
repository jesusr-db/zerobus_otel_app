"""Data models for logs API."""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class LogEntry(BaseModel):
    """Individual log entry from logs_synced table."""
    event_name: Optional[str] = ""
    trace_id: Optional[str] = ""
    span_id: Optional[str] = ""
    log_timestamp: datetime
    observed_timestamp: datetime
    severity_text: Optional[str] = "INFO"
    body: str
    service_name: str
    attributes: Dict[str, Any]  # Parsed from JSON string


class LogsResponse(BaseModel):
    """Response for logs list endpoint."""
    logs: List[LogEntry]
    total_count: int
    page: int
    page_size: int
    has_more: bool
    severity_counts: Dict[str, int]


class SeverityTimelinePoint(BaseModel):
    """Single point in severity timeline."""
    timestamp: datetime
    ERROR: int
    WARN: int
    INFO: int
    DEBUG: int


class SeverityTimelineResponse(BaseModel):
    """Response for severity timeline endpoint."""
    timeline: List[SeverityTimelinePoint]
    service_name: str
    time_range: str
