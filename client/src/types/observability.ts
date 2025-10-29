export interface MetricsSnapshot {
  latency_p50: number;
  latency_p95: number;
  latency_p99: number;
  avg_duration_ms: number;
  max_duration_ms: number;
  error_count: number;
  error_rate: number;
  request_count: number;
  requests_per_second: number;
}

export interface ServiceHealth {
  service_name: string;
  health_status: 'healthy' | 'warning' | 'critical';
  current_latency_p50: number;
  current_latency_p95: number;
  current_latency_p99: number;
  avg_duration_ms: number;
  max_duration_ms: number;
  error_count: number;
  error_rate: number;
  request_count: number;
  requests_per_second: number;
}

export interface MetricsTimeSeries {
  timestamp: string;
  latency_p95: number;
  avg_duration_ms: number;
  error_count: number;
  request_count: number;
}

export interface ServiceMetricsDetail {
  service_name: string;
  current: MetricsSnapshot;
  trends: MetricsTimeSeries[];
  baseline: MetricsSnapshot;
}

export interface DependencyInfo {
  service_name: string;
  call_count: number;
  health_status: string;
}

export interface ServiceDependencies {
  service_name: string;
  inbound: DependencyInfo[];
  outbound: DependencyInfo[];
}

export interface GraphNode {
  id: string;
  health: 'healthy' | 'warning' | 'critical';
  errorRate: number;
  requestCount: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  callCount: number;
}

export interface DependencyGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface WarehouseInfo {
  warehouse_id: string;
  warehouse_name: string;
  status: string;
}

export type TimeRange = '15m' | '1h' | '24h';
