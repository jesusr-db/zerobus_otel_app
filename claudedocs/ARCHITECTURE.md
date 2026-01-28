# Observability Dashboard - System Architecture

**Last Updated**: 2026-01-14
**Version**: 1.0
**Data Backend**: Lakebase (PostgreSQL)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Data Architecture](#data-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Backend Architecture](#backend-architecture)
6. [Panel-to-API-to-Database Mapping](#panel-to-api-to-database-mapping)
7. [Data Flow Diagrams](#data-flow-diagrams)
8. [Authentication & Security](#authentication--security)

---

## System Overview

The Observability Dashboard is a full-stack web application for monitoring distributed systems through traces, metrics, and logs. It provides real-time visualization of service health, dependencies, and performance metrics.

### Key Features
- **Service Health Dashboard**: Real-time service status cards with key metrics
- **Dependency Map**: Interactive force-directed graph showing service relationships
- **Metrics KPIs**: Dynamic metric panels with baseline comparison
- **Logs Explorer**: Advanced search and filtering with severity timeline
- **Trace Analysis**: Waterfall visualization of distributed traces
- **Service Details**: Sliding panel with detailed metrics, trends, and dependencies

### Architecture Pattern
- **Frontend**: Single Page Application (SPA) with React + TypeScript
- **Backend**: RESTful API with FastAPI (Python)
- **Database**: Lakebase (Databricks-hosted PostgreSQL)
- **Deployment**: Databricks Apps platform

---

## Technology Stack

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | React 18 | UI component library |
| Language | TypeScript | Type-safe JavaScript |
| Build Tool | Vite | Fast development and bundling |
| State Management | React Query | Server state caching and synchronization |
| Routing | React Router v6 | Client-side navigation |
| UI Components | shadcn/ui + Tailwind CSS | Pre-built accessible components |
| Charts | Recharts | Data visualization |
| Graph Visualization | D3.js | Force-directed dependency graph |
| HTTP Client | Fetch API | API communication |

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | FastAPI | High-performance async API |
| Language | Python 3.11 | Backend logic |
| Package Manager | uv | Fast Python dependency management |
| Database Driver | psycopg2 | PostgreSQL connection |
| Databricks SDK | databricks-sdk | Workspace integration |
| Validation | Pydantic v2 | Request/response validation |
| Logging | Python logging | Structured logging |

### Database
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Primary Database | Lakebase (PostgreSQL) | Observability data storage |
| Schema | `zerobus_sdp` | Observability data namespace |
| Tables | 6 core tables | Traces, metrics, logs, dependencies |

### Deployment
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Platform | Databricks Apps | Hosting and deployment |
| Assets Bundle | databricks.yml | Infrastructure as code |
| Frontend Serving | FastAPI StaticFiles | Serve React build artifacts |
| Authentication | Databricks OAuth | User authentication via X-Forwarded-Access-Token |

---

## Data Architecture

### Database: Lakebase PostgreSQL

**Connection Details**:
- **Instance**: `zerobus-dev`
- **Catalog**: `zerobus_sdp`
- **Schema**: `zerobus_sdp`
- **Host**: Auto-detected from instance name (currently hardcoded)
- **Port**: 5432
- **Auth**: OAuth token passed via X-Forwarded-Access-Token header

### Core Tables

#### 1. **traces_assembled_synced**
Stores assembled distributed traces with all span details.

| Column | Type | Description |
|--------|------|-------------|
| `trace_id` | TEXT | Unique trace identifier |
| `trace_start` | TIMESTAMP | Trace start time |
| `services_involved` | TEXT[] | Array of service names in trace |
| `span_count` | INT | Number of spans in trace |
| `total_trace_duration_ms` | FLOAT | Total trace duration |
| `span_details` | JSONB | Array of span objects with service_name, duration_ms, is_error |

**Usage**: Traces panel, Service metrics, Dependency graph, Waterfall visualization

#### 2. **service_dependencies_synced**
Pre-computed service dependency relationships.

| Column | Type | Description |
|--------|------|-------------|
| `source_service` | TEXT | Calling service name |
| `target_service` | TEXT | Called service name |
| `call_count` | INT | Number of calls between services |
| `last_seen` | TIMESTAMP | Most recent interaction |

**Usage**: Dependency map, Service detail panel dependencies section

#### 3. **metrics_1min_synced**
Time-series metrics aggregated in 1-minute buckets.

| Column | Type | Description |
|--------|------|-------------|
| `service_name` | TEXT | Service identifier |
| `metric_name` | TEXT | Metric name (e.g., http.server.duration) |
| `metric_type` | TEXT | Metric type: histogram, gauge, sum |
| `timestamp` | TIMESTAMP | Metric timestamp |
| `value` | FLOAT | Aggregated metric value |
| `unit` | TEXT | Metric unit (ms, count, etc.) |
| `attributes` | JSONB | Additional metric dimensions |

**Usage**: Metrics KPIs panel, Service trends

#### 4. **logs_synced**
Application logs with structured attributes.

| Column | Type | Description |
|--------|------|-------------|
| `event_name` | TEXT | Log event name |
| `trace_id` | TEXT | Associated trace ID (nullable) |
| `span_id` | TEXT | Associated span ID (nullable) |
| `log_timestamp` | TIMESTAMP | When log was created |
| `observed_timestamp` | TIMESTAMP | When log was received |
| `severity_text` | TEXT | Log severity: ERROR, WARN, INFO, DEBUG |
| `body` | TEXT | Log message body |
| `service_name` | TEXT | Service that generated log (nullable) |
| `attributes` | JSONB | Structured log attributes |

**Usage**: Logs panel, Severity timeline

#### 5. **spans_raw** (Referenced but not primary)
Raw span data before aggregation.

**Usage**: Historical reference, debugging

#### 6. **metrics_raw** (Referenced but not primary)
Raw metric data before aggregation.

**Usage**: Historical reference, debugging

---

## Frontend Architecture

### Component Hierarchy

```
App.tsx (Root)
├── BrowserRouter
├── TimeRangeProvider (Global time range state)
├── ServiceProvider (Global selected service state)
└── Layout
    ├── Sidebar Navigation
    ├── Header (TimeRangeSelector)
    ├── Main Content (Routes)
    │   ├── DashboardView
    │   ├── DependencyMapView
    │   ├── ServicesListView
    │   ├── MetricsView
    │   ├── LogsView
    │   ├── TracesView
    │   └── TracingAnalysisView
    ├── ServiceDetailPanel (Conditional)
    └── TraceDetailPanel (Conditional)
```

### Key React Contexts

#### TimeRangeContext
- **State**: `timeRange` (5m | 1h | 1d | 1w)
- **Purpose**: Global time range selection for all panels
- **Used By**: All views, ServiceDetailPanel

#### ServiceContext
- **State**: `selectedService` (string | null)
- **Purpose**: Track which service is selected for detail panel
- **Used By**: Dashboard, Dependency Map, Layout

### Routing Configuration

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | DashboardView | Service health cards grid |
| `/map` | DependencyMapView | Force-directed service graph |
| `/services` | ServicesListView | Sortable service table |
| `/metrics` | MetricsView | Service-specific KPI panels |
| `/logs` | LogsView | Log search and filtering |
| `/traces` | TracesView | Trace list with filtering |
| `/tracing-analysis` | TracingAnalysisView | Waterfall trace visualization |

---

## Backend Architecture

### API Router Structure

```
server/
├── app.py (FastAPI application)
├── config.py (Environment configuration)
├── models/
│   ├── observability.py (ServiceHealth, TraceInfo, etc.)
│   └── logs.py (LogEntry, LogsResponse)
├── services/
│   ├── lakebase_manager.py (PostgreSQL connection)
│   └── warehouse_manager.py (SQL Warehouse connection)
└── routers/
    ├── services.py (Service health and metrics)
    ├── dependencies.py (Dependency graph)
    ├── traces.py (Trace list and waterfall)
    ├── metrics_kpis.py (Dynamic metrics panels)
    ├── logs.py (Log search and timeline)
    ├── user.py (User info)
    └── lakebase_validation.py (DB validation)
```

### Data Manager Pattern

**LakebaseManager** (`server/services/lakebase_manager.py`):
- Manages PostgreSQL connection pool
- Handles OAuth token refresh
- Executes parameterized queries
- Converts PostgreSQL results to Python dicts

**WarehouseManager** (`server/services/warehouse_manager.py`):
- Manages Databricks SQL Warehouse connections
- Executes Spark SQL queries
- Alternative backend (not currently used)

### Configuration (`server/config.py`)

```python
DATA_BACKEND = "lakebase"  # Backend selection
LAKEBASE_INSTANCE_NAME = "zerobus-dev"
LAKEBASE_SCHEMA_NAME = "zerobus_sdp"
LAKEBASE_CATALOG_NAME = "zerobus_sdp"
OBSERVABILITY_TABLE_PREFIX = "jmr_demo.zerobus_sdp"  # Warehouse fallback
```

---

## Panel-to-API-to-Database Mapping

### 1. Dashboard View

**Frontend**: `client/src/pages/DashboardView.tsx`

**API Endpoint**: `GET /api/services/list?time_range={timeRange}`

**Backend Router**: `server/routers/services.py:38` (`get_services`)

**Database Query**:
```sql
-- Uses traces_assembled_synced + metrics_1min_synced
WITH current_spans AS (
  SELECT
    span_value->>'service_name' as service_name,
    (span_value->>'duration_ms')::float as duration_ms,
    (span_value->>'is_error')::boolean as is_error
  FROM zerobus_sdp.traces_assembled_synced t
  CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
  WHERE t.trace_start >= NOW() - INTERVAL '{interval}'
)
SELECT
  service_name,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as current_latency_p95,
  CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) as error_rate,
  COUNT(*) as request_count,
  COUNT(*) / {seconds} as requests_per_second,
  CASE
    WHEN error_rate > 0.05 THEN 'critical'
    WHEN current_latency_p95 > baseline_latency_p95 THEN 'warning'
    ELSE 'healthy'
  END as health_status
FROM current_spans
GROUP BY service_name
```

**Tables Used**:
- `traces_assembled_synced` (span_details JSONB)
- `metrics_1min_synced` (for baseline comparison)

**Response Model**: `ServiceHealth[]`
```typescript
{
  service_name: string;
  health_status: "healthy" | "warning" | "critical";
  current_latency_p95: number;
  error_rate: number;
  request_count: number;
  requests_per_second: number;
}
```

---

### 2. Dependency Map View

**Frontend**: `client/src/pages/DependencyMapView.tsx`

**API Endpoint**: `GET /api/dependencies/graph?time_range={timeRange}`

**Backend Router**: `server/routers/dependencies.py:29` (`get_dependency_graph`)

**Database Query**:
```sql
-- Node health from traces_assembled_synced
WITH current_spans AS (
  SELECT
    span_value->>'service_name' as service_name,
    (span_value->>'duration_ms')::float as duration_ms,
    (span_value->>'is_error')::boolean as is_error
  FROM zerobus_sdp.traces_assembled_synced t
  CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
  WHERE t.trace_start >= NOW() - INTERVAL '{interval}'
),
service_health AS (
  SELECT
    service_name,
    SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
    CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) as error_rate,
    CASE
      WHEN latency_p50 > baseline_latency_p50 THEN 'critical'
      WHEN request_count / {seconds} > baseline_rps THEN 'warning'
      ELSE 'healthy'
    END as health_status
  FROM current_spans
  GROUP BY service_name
)
SELECT
  'node' as row_type,
  s.service_name as id,
  COALESCE(h.health_status, 'healthy') as health,
  COALESCE(h.error_rate, 0.0) as "errorRate",
  COALESCE(h.request_count, 0) as "requestCount"
FROM (
  SELECT DISTINCT source_service as service_name FROM zerobus_sdp.service_dependencies_synced
  UNION
  SELECT DISTINCT target_service as service_name FROM zerobus_sdp.service_dependencies_synced
) s
LEFT JOIN service_health h ON s.service_name = h.service_name

UNION ALL

-- Edges from service_dependencies_synced
SELECT
  'edge' as row_type,
  d.source_service as source,
  d.target_service as target,
  d.call_count as "callCount"
FROM zerobus_sdp.service_dependencies_synced d
```

**Tables Used**:
- `service_dependencies_synced` (edges and service list)
- `traces_assembled_synced` (node health status)

**Response Model**: `DependencyGraph`
```typescript
{
  nodes: Array<{
    id: string;
    health: "healthy" | "warning" | "critical";
    errorRate: number;
    requestCount: number;
  }>;
  edges: Array<{
    source: string;
    target: string;
    callCount: number;
  }>;
}
```

**Visualization**: D3.js force-directed graph in `ServiceGraph` component

---

### 3. Service Detail Panel (Popup)

**Frontend**: `client/src/components/ServiceDetailPanel.tsx`

**Triggered By**: Click on Dashboard card or Dependency Map node

**API Endpoints**:
1. `GET /api/services/{service_name}/metrics?time_range={timeRange}`
2. `GET /api/services/{service_name}/dependencies`

#### 3.1 Service Metrics API

**Backend Router**: `server/routers/services.py:230` (`get_service_metrics`)

**Database Query** (Current Metrics):
```sql
WITH service_spans AS (
  SELECT
    span_value->>'service_name' as service_name,
    (span_value->>'duration_ms')::float as duration_ms,
    (span_value->>'is_error')::boolean as is_error
  FROM zerobus_sdp.traces_assembled_synced t
  CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
  WHERE span_value->>'service_name' = '{service_name}'
    AND t.trace_start >= NOW() - INTERVAL '{interval}'
)
SELECT
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as latency_p50,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as latency_p99,
  AVG(duration_ms) as avg_duration_ms,
  SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
  CAST(SUM(CASE WHEN is_error THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) as error_rate,
  COUNT(*) as request_count,
  COUNT(*) / {seconds} as requests_per_second
FROM service_spans
```

**Database Query** (Trends):
```sql
WITH service_spans AS (
  SELECT
    span_value->>'service_name' as service_name,
    (span_value->>'duration_ms')::float as duration_ms,
    (span_value->>'is_error')::boolean as is_error,
    date_trunc('minute', t.trace_start) as time_bucket
  FROM zerobus_sdp.traces_assembled_synced t
  CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
  WHERE span_value->>'service_name' = '{service_name}'
    AND t.trace_start >= NOW() - INTERVAL '{interval}'
)
SELECT
  time_bucket as timestamp,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
  AVG(duration_ms) as avg_duration_ms,
  SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
  COUNT(*) as request_count
FROM service_spans
GROUP BY time_bucket
ORDER BY time_bucket
```

**Tables Used**:
- `traces_assembled_synced` (span_details JSONB)

**Response Model**: `ServiceMetricsDetail`
```typescript
{
  current: {
    latency_p50: number;
    latency_p95: number;
    latency_p99: number;
    avg_duration_ms: number;
    error_rate: number;
    request_count: number;
    requests_per_second: number;
  };
  baseline: { /* same structure */ };
  trends: Array<{
    timestamp: string;
    latency_p95: number;
    avg_duration_ms: number;
    error_count: number;
    request_count: number;
  }>;
}
```

#### 3.2 Service Dependencies API

**Backend Router**: `server/routers/services.py` (dependencies endpoint)

**Database Query**:
```sql
-- Inbound dependencies
SELECT
  d.source_service as service_name,
  d.call_count,
  h.health_status
FROM zerobus_sdp.service_dependencies_synced d
LEFT JOIN service_health h ON d.source_service = h.service_name
WHERE d.target_service = '{service_name}'

UNION ALL

-- Outbound dependencies
SELECT
  d.target_service as service_name,
  d.call_count,
  h.health_status
FROM zerobus_sdp.service_dependencies_synced d
LEFT JOIN service_health h ON d.target_service = h.service_name
WHERE d.source_service = '{service_name}'
```

**Tables Used**:
- `service_dependencies_synced`
- `traces_assembled_synced` (for health status)

**Charts**: Recharts LineCharts for P95 latency, avg duration, error count, request count

---

### 4. Metrics KPIs Panel

**Frontend**: `client/src/pages/MetricsView.tsx` + `client/src/components/MetricsKPIPanel.tsx`

**API Endpoint**: `GET /api/metrics/{service_name}/kpis?time_range={timeRange}`

**Backend Router**: `server/routers/metrics_kpis.py:38` (`get_service_kpis`)

**Database Query**:
```sql
-- Dynamic metric discovery
WITH available_metrics AS (
  SELECT DISTINCT
    metric_name,
    metric_type,
    unit
  FROM zerobus_sdp.metrics_1min_synced
  WHERE service_name = '{service_name}'
    AND timestamp >= NOW() - INTERVAL '{interval}'
),
current_metrics AS (
  SELECT
    metric_name,
    AVG(value) as current_value
  FROM zerobus_sdp.metrics_1min_synced
  WHERE service_name = '{service_name}'
    AND timestamp >= NOW() - INTERVAL '{interval}'
  GROUP BY metric_name
),
baseline_metrics AS (
  SELECT
    metric_name,
    AVG(value) as baseline_value
  FROM zerobus_sdp.metrics_1min_synced
  WHERE service_name = '{service_name}'
    AND timestamp >= NOW() - INTERVAL '{interval}' - INTERVAL '{interval}'
    AND timestamp < NOW() - INTERVAL '{interval}'
  GROUP BY metric_name
)
SELECT
  am.metric_name,
  am.metric_type,
  am.unit,
  cm.current_value,
  bm.baseline_value,
  CASE
    WHEN (cm.current_value - bm.baseline_value) / bm.baseline_value > 0.05 THEN 'up'
    WHEN (cm.current_value - bm.baseline_value) / bm.baseline_value < -0.05 THEN 'down'
    ELSE 'stable'
  END as trend
FROM available_metrics am
LEFT JOIN current_metrics cm ON am.metric_name = cm.metric_name
LEFT JOIN baseline_metrics bm ON am.metric_name = bm.metric_name
```

**Tables Used**:
- `metrics_1min_synced` (all columns)

**Response Model**: Grouped by metric type
```typescript
{
  histogram: Array<{
    name: string;
    current_value: number;
    baseline_value: number;
    unit: string;
    trend: "up" | "down" | "stable";
  }>;
  gauge: Array<{ /* same */ }>;
  sum: Array<{ /* same */ }>;
}
```

**UI**: KPI cards with trend indicators (↑↓→) and percentage change

---

### 5. Logs Panel

**Frontend**: `client/src/pages/LogsView.tsx` + `client/src/components/LogDetailsPanel.tsx`

**API Endpoints**:
1. `GET /api/logs/list` (with filters)
2. `GET /api/logs/severity-timeline`

#### 5.1 Logs List API

**Backend Router**: `server/routers/logs.py:146` (`get_logs`)

**Query Parameters**:
- `service_name` (optional) - Filter by service
- `time_range` (5m|1h|1d|1w) - Time window
- `search` (optional) - Full-text search in body and attributes
- `search_mode` (simple|advanced) - Search syntax
- `severity_filter` (optional) - Comma-separated: ERROR,WARN,INFO,DEBUG
- `trace_id` (optional) - Filter by trace ID
- `page` (default: 1) - Pagination page
- `page_size` (default: 100, max: 500) - Results per page

**Database Query**:
```sql
-- Main logs query with filtering
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
WHERE log_timestamp >= NOW() - INTERVAL '{interval}'
  AND service_name = %s  -- if service filter applied
  AND (body ILIKE %s OR attributes::text ILIKE %s)  -- if search applied
  AND severity_text IN (%s, %s)  -- if severity filter applied
  AND trace_id = %s  -- if trace_id filter applied
ORDER BY log_timestamp DESC
LIMIT %s OFFSET %s
```

**Advanced Search Syntax**:
- `body:database` - Search only in body field
- `severity:ERROR` - Filter by severity
- `trace_id:abc123` - Filter by trace ID
- `attributes.error.type:ConnectionError` - Search in JSONB attributes
- Combined: `severity:ERROR AND body:database`

**Tables Used**:
- `logs_synced` (all columns)

**Response Model**: `LogsResponse`
```typescript
{
  logs: Array<{
    event_name: string;
    trace_id?: string;
    span_id?: string;
    log_timestamp: string;
    observed_timestamp?: string;
    severity_text: "ERROR" | "WARN" | "INFO" | "DEBUG";
    body: string;
    service_name: string;
    attributes: Record<string, any>;
  }>;
  total_count: number;
  page: number;
  page_size: number;
  has_more: boolean;
  severity_counts: Record<string, number>;
}
```

#### 5.2 Severity Timeline API

**Backend Router**: `server/routers/logs.py:314` (`get_severity_timeline`)

**Database Query**:
```sql
SELECT
  TO_TIMESTAMP(FLOOR(EXTRACT(EPOCH FROM log_timestamp) / {granularity}) * {granularity}) as bucket,
  COUNT(*) FILTER (WHERE severity_text = 'ERROR') as ERROR,
  COUNT(*) FILTER (WHERE severity_text = 'WARN') as WARN,
  COUNT(*) FILTER (WHERE severity_text = 'INFO') as INFO,
  COUNT(*) FILTER (WHERE severity_text = 'DEBUG') as DEBUG
FROM zerobus_sdp.logs_synced
WHERE log_timestamp >= NOW() - INTERVAL '{interval}'
  AND service_name = %s  -- if service filter applied
GROUP BY bucket
ORDER BY bucket ASC
```

**Granularity** (auto-adjusted):
- 5m range → 30-second buckets
- 1h range → 5-minute buckets
- 1d range → 1-hour buckets
- 1w range → 1-day buckets

**Tables Used**:
- `logs_synced` (log_timestamp, severity_text)

**Response Model**: `SeverityTimelineResponse`
```typescript
{
  timeline: Array<{
    timestamp: string;
    ERROR: number;
    WARN: number;
    INFO: number;
    DEBUG: number;
  }>;
  service_name?: string;
  time_range: string;
}
```

**Visualization**: Stacked area chart with Recharts showing severity distribution over time

---

### 6. Traces Panel

**Frontend**: `client/src/pages/TracesView.tsx`

**API Endpoint**: `GET /api/traces?time_range={timeRange}`

**Backend Router**: `server/routers/traces.py:28` (`get_all_traces`)

**Database Query**:
```sql
SELECT
  trace_id,
  trace_start,
  services_involved,
  span_count,
  total_trace_duration_ms,
  span_details
FROM zerobus_sdp.traces_assembled_synced
WHERE trace_start >= NOW() - INTERVAL '{interval}'
ORDER BY trace_start DESC
LIMIT 100
```

**Tables Used**:
- `traces_assembled_synced` (all columns)

**Response Model**: `TraceInfo[]`
```typescript
{
  trace_id: string;
  trace_start: string;
  services_involved: string[];
  span_count: number;
  total_trace_duration_ms: number;
  span_details: Array<{
    service_name: string;
    duration_ms: number;
    is_error: boolean;
  }>;
}
```

**UI**: Sortable table with trace_id, services, duration, span count

---

### 7. Tracing Analysis (Waterfall View)

**Frontend**: `client/src/pages/TracingAnalysisView.tsx`

**API Endpoint**: `GET /api/traces/waterfall/{trace_id}`

**Backend Router**: `server/routers/traces.py` (waterfall endpoint)

**Database Query**:
```sql
SELECT
  trace_id,
  span_details
FROM zerobus_sdp.traces_assembled_synced
WHERE trace_id = '{trace_id}'
```

**JSONB span_details Structure**:
```json
[
  {
    "span_id": "abc123",
    "parent_span_id": null,
    "service_name": "frontend",
    "operation_name": "GET /api/users",
    "start_time": "2026-01-14T12:00:00Z",
    "duration_ms": 150.5,
    "is_error": false,
    "attributes": {}
  }
]
```

**Tables Used**:
- `traces_assembled_synced` (span_details JSONB)

**Response Model**: `TraceWaterfall`
```typescript
{
  trace_id: string;
  spans: Array<{
    span_id: string;
    parent_span_id?: string;
    service_name: string;
    operation_name: string;
    start_time: string;
    duration_ms: number;
    is_error: boolean;
    attributes: Record<string, any>;
  }>;
}
```

**Visualization**: Custom waterfall chart showing span hierarchy with:
- Horizontal bars representing span duration
- Indentation showing parent-child relationships
- Color coding by service
- Error highlighting

---

### 8. Services List View

**Frontend**: `client/src/pages/ServicesListView.tsx`

**API Endpoint**: `GET /api/services/list?time_range={timeRange}` (same as Dashboard)

**Backend Router**: `server/routers/services.py:38` (`get_services`)

**Tables Used**: Same as Dashboard View
- `traces_assembled_synced`
- `metrics_1min_synced`

**Response Model**: Same as Dashboard View (`ServiceHealth[]`)

**UI**: Sortable/filterable table with columns:
- Service Name
- Health Status
- P95 Latency
- Error Rate
- Request Count
- RPS

---

## Data Flow Diagrams

### Service Health Data Flow

```
User Browser
    ↓
GET /api/services/list?time_range=1h
    ↓
FastAPI Router (services.py)
    ↓
LakebaseManager.execute_query()
    ↓
PostgreSQL (zerobus-dev)
    ↓
Query: traces_assembled_synced (JSONB span_details)
    ↓
Aggregate: P95 latency, error rate, request count
    ↓
Baseline comparison: Previous time window
    ↓
Health status calculation: healthy/warning/critical
    ↓
Return ServiceHealth[]
    ↓
React Query caches response
    ↓
DashboardView renders cards
    ↓
User clicks card
    ↓
ServiceContext.setSelectedService()
    ↓
Layout renders ServiceDetailPanel
    ↓
Panel fetches /api/services/{name}/metrics
    ↓
LakebaseManager queries traces_assembled_synced
    ↓
Returns metrics + trends + dependencies
    ↓
Recharts renders line charts
```

### Dependency Graph Data Flow

```
User Browser
    ↓
GET /api/dependencies/graph?time_range=1h
    ↓
FastAPI Router (dependencies.py)
    ↓
LakebaseManager.execute_query()
    ↓
PostgreSQL (zerobus-dev)
    ↓
Query 1: service_dependencies_synced (edges + node list)
Query 2: traces_assembled_synced (node health)
    ↓
UNION ALL: Combine nodes + edges
    ↓
Return DependencyGraph { nodes, edges }
    ↓
React Query caches response
    ↓
DependencyMapView renders ServiceGraph
    ↓
D3.js force simulation
    ↓
Render: SVG circles (nodes) + lines (edges)
    ↓
Color nodes by health status
    ↓
User clicks node
    ↓
ServiceContext.setSelectedService()
    ↓
Layout renders ServiceDetailPanel
```

### Logs Search Data Flow

```
User Browser
    ↓
GET /api/logs/list?search=error&severity_filter=ERROR,WARN
    ↓
FastAPI Router (logs.py)
    ↓
Parse search query (simple/advanced mode)
    ↓
Build SQL WHERE clause with parameters
    ↓
LakebaseManager.execute_query()
    ↓
PostgreSQL (zerobus-dev)
    ↓
Query: logs_synced with filters
    ↓
Full-text search: body ILIKE %search% OR attributes::text ILIKE %search%
Severity filter: severity_text IN ('ERROR', 'WARN')
Pagination: LIMIT/OFFSET
    ↓
Parse JSONB attributes to dict
    ↓
Return LogsResponse { logs, total_count, severity_counts }
    ↓
React Query caches response
    ↓
LogsView renders table + pagination
    ↓
User clicks log entry
    ↓
LogDetailsPanel shows full attributes
```

---

## Authentication & Security

### Databricks OAuth Flow

1. User accesses app URL: `https://<workspace>/apps/<app-name>`
2. Databricks authenticates user via OAuth
3. Databricks injects `X-Forwarded-Access-Token` header into all requests
4. FastAPI extracts token: `request.headers.get("X-Forwarded-Access-Token")`
5. Token passed to LakebaseManager for database authentication
6. Token refreshed automatically every 15 minutes

### Database Permissions

**Service Principal**: App's service principal needs:
- `CAN_USE` on Lakebase instance (`zerobus-dev`)
- `CAN_CONNECT_AND_CREATE` on database (`zerobus_sdp`)
- Read access to all observability tables

**Grant Permissions**:
```sql
-- Granted via resources/grant_permissions_job.yml
GRANT USAGE ON DATABASE zerobus_sdp TO SERVICE_PRINCIPAL;
GRANT SELECT ON ALL TABLES IN SCHEMA zerobus_sdp.public TO SERVICE_PRINCIPAL;
```

### Security Features

- **No API Keys**: Uses OAuth token from Databricks
- **Token Refresh**: Automatic token rotation every 15 minutes
- **Parameterized Queries**: All SQL uses `%s` placeholders to prevent injection
- **CORS**: Restricted to Databricks workspace domains
- **No Secrets in Code**: All credentials via environment variables

---

## Performance Optimizations

### Frontend
- **React Query Caching**: 30-second stale time for all queries
- **Auto-refresh**: Queries refetch every 30 seconds in background
- **Lazy Loading**: Routes code-split with React.lazy()
- **Memoization**: ServiceGraph uses useMemo for expensive calculations
- **Virtual Scrolling**: Logs and traces panels support infinite scroll

### Backend
- **Connection Pooling**: PostgreSQL connection pool (5-20 connections)
- **Query Optimization**: Indexed queries on timestamp, service_name, trace_id
- **JSONB Indexing**: GIN indexes on span_details and attributes columns
- **Pagination**: Limit/offset for large result sets (max 500 logs per page)
- **Async Endpoints**: FastAPI async handlers for concurrent request handling

### Database
- **Aggregation Tables**: Pre-computed service_dependencies_synced
- **1-Minute Metrics**: Pre-aggregated metrics_1min_synced
- **JSONB Arrays**: Efficient storage of span_details in single JSONB column
- **Time-Based Partitioning**: Traces partitioned by trace_start (future optimization)

---

## Deployment Architecture

### Databricks Apps Platform

```
User Browser
    ↓
https://<workspace>.cloud.databricks.com/apps/o11y-jmr
    ↓
Databricks OAuth Gateway
    ↓
Injects X-Forwarded-Access-Token
    ↓
App Container (uvicorn)
    ├── FastAPI Backend (port 8000)
    │   ├── /api/* endpoints
    │   └── /health endpoint
    └── Static Files (/)
        └── React SPA (client/build/)
            ├── index.html
            └── assets/*.js, *.css
```

### Build Pipeline

```
Local Development:
  ./watch.sh → Frontend (Vite) + Backend (uvicorn) with hot reload

Deployment:
  1. cd client && bun run build
     → Outputs to client/build/
  2. databricks bundle deploy --target dogfood
     → Uploads app.yml + server/ + client/build/
     → Starts uvicorn server
     → Serves React app at /
     → API available at /api/*
```

### Environment Variables (app.yml)

```yaml
env:
  - name: CATALOG_NAME
    value: jmr_demo
  - name: SCHEMA_NAME
    value: zerobus_sdp
  - name: DATA_BACKEND
    value: lakebase
  - name: LAKEBASE_INSTANCE_NAME
    value: zerobus-dev
  - name: LAKEBASE_DATABASE_NAME
    value: zerobus_sdp
  - name: LAKEBASE_CATALOG_NAME
    value: zerobus_sdp
  - name: LAKEBASE_SCHEMA_NAME
    value: zerobus_sdp
  - name: LAKEBASE_HOST
    value: instance-fbdab8c4-86f6-400a-ac42-632a91017360.database.cloud.databricks.com
  - name: LAKEBASE_PORT
    value: "5432"
  - name: ENVIRONMENT
    value: production

resources:
  - name: lakebase-instance
    database_instance:
      id: zerobus-dev
      permission: CAN_USE
  - name: warehouse
    sql_warehouse:
      auto_detect: true
      permission: CAN_USE
```

---

## Known Issues & Future Improvements

### Current Issues
1. **Hardcoded Lakebase Host**: Host address is hardcoded in app.yml instead of auto-detected (Issue #002 in PROJECT_PLAN.md)
2. **Metrics Aggregation**: Metrics view shows only latest events instead of time-based aggregation
3. **No Waterfall Hierarchy**: Waterfall view needs parent-child span relationship visualization
4. **Logs Null Values**: Some logs have null service_name or body fields

### Planned Improvements
1. **Auto-detect Lakebase Host**: Use Databricks SDK to discover instance host dynamically
2. **Time-based Investigation View**: Unified timeline with synchronized metrics/traces/logs
3. **Enhanced Search**: Advanced log search with regex and attribute path navigation
4. **Alert Thresholds**: User-configurable alert rules for critical/warning states
5. **Export Functionality**: CSV/JSON export for logs and traces
6. **Real-time Updates**: WebSocket connection for live log streaming

---

## Appendix: Quick Reference

### API Endpoints Summary

| Endpoint | Method | Purpose | Database Tables |
|----------|--------|---------|-----------------|
| `/api/services/list` | GET | Service health list | traces_assembled_synced, metrics_1min_synced |
| `/api/services/{name}/metrics` | GET | Service detailed metrics | traces_assembled_synced |
| `/api/services/{name}/dependencies` | GET | Service dependencies | service_dependencies_synced, traces_assembled_synced |
| `/api/dependencies/graph` | GET | Dependency graph | service_dependencies_synced, traces_assembled_synced |
| `/api/metrics/{name}/kpis` | GET | Dynamic KPI panels | metrics_1min_synced |
| `/api/logs/list` | GET | Log search with filters | logs_synced |
| `/api/logs/severity-timeline` | GET | Severity timeline | logs_synced |
| `/api/traces` | GET | Trace list | traces_assembled_synced |
| `/api/traces/waterfall/{id}` | GET | Trace waterfall | traces_assembled_synced |
| `/api/user/me` | GET | Current user info | Databricks API |
| `/health` | GET | Health check | N/A |

### Database Schema Summary

| Table | Primary Key | Key Columns | Purpose |
|-------|-------------|-------------|---------|
| `traces_assembled_synced` | trace_id | trace_start, span_details (JSONB) | Distributed traces |
| `service_dependencies_synced` | (source, target) | call_count | Service relationships |
| `metrics_1min_synced` | (service, metric, timestamp) | value, metric_type | Time-series metrics |
| `logs_synced` | (event_name, timestamp) | severity_text, body, attributes (JSONB) | Application logs |

### Time Range Intervals

| Time Range | Interval SQL | Seconds | Metric Granularity |
|------------|--------------|---------|-------------------|
| 5m | 5 MINUTE | 300 | 30 seconds |
| 1h | 1 HOUR | 3600 | 5 minutes |
| 1d | 1 DAY | 86400 | 1 hour |
| 1w | 7 DAY | 604800 | 1 day |

---

**Document Version**: 1.0
**Last Updated**: 2026-01-14
**Maintained By**: Observability Team
