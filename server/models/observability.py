from pydantic import BaseModel
from typing import List, Literal
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
