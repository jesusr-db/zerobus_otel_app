from pydantic import BaseModel, field_serializer
from typing import List, Literal, Union
from datetime import datetime


class MetricsSnapshot(BaseModel):
    latency_p50: float
    latency_p95: float
    latency_p99: float
    avg_duration_ms: float
    max_duration_ms: float
    error_count: int
    error_rate: float
    request_count: int
    requests_per_second: float


class ServiceHealth(BaseModel):
    service_name: str
    health_status: Literal['healthy', 'warning', 'critical']
    current_latency_p50: float
    current_latency_p95: float
    current_latency_p99: float
    avg_duration_ms: float
    max_duration_ms: float
    error_count: int
    error_rate: float
    request_count: int
    requests_per_second: float


class MetricsTimeSeries(BaseModel):
    timestamp: datetime
    latency_p95: float
    avg_duration_ms: float
    error_count: int
    request_count: int


class ServiceMetricsDetail(BaseModel):
    service_name: str
    current: MetricsSnapshot
    trends: List[MetricsTimeSeries]
    baseline: MetricsSnapshot


class DependencyInfo(BaseModel):
    service_name: str
    call_count: int
    health_status: str


class ServiceDependencies(BaseModel):
    service_name: str
    inbound: List[DependencyInfo]
    outbound: List[DependencyInfo]


class GraphNode(BaseModel):
    id: str
    health: Literal['healthy', 'warning', 'critical']
    errorRate: float
    requestCount: int


class GraphEdge(BaseModel):
    source: str
    target: str
    callCount: int


class DependencyGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class WarehouseInfo(BaseModel):
    warehouse_id: str
    warehouse_name: str
    status: str


class TraceInfo(BaseModel):
    trace_id: str
    trace_start: Union[str, datetime]
    services_involved: List[str]
    total_duration_ms: float
    span_count: int
    
    @field_serializer('trace_start')
    def serialize_trace_start(self, value: Union[str, datetime]) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return value


class SpanDetail(BaseModel):
    service_name: str
    total_duration_ms: float


class TraceDetail(BaseModel):
    trace_id: str
    trace_start: Union[str, datetime]
    spans: List[SpanDetail]
    
    @field_serializer('trace_start')
    def serialize_trace_start(self, value: Union[str, datetime]) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return value


class SpanWaterfall(BaseModel):
    span_id: str
    name: str
    service_name: str
    duration_ms: float
    start_offset_ms: float
    parent_span_id: str | None
    is_error: bool = False


class TraceWaterfall(BaseModel):
    trace_id: str
    trace_start: Union[str, datetime]
    total_duration_ms: float
    spans: List[SpanWaterfall]
    
    @field_serializer('trace_start')
    def serialize_trace_start(self, value: Union[str, datetime]) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return value
