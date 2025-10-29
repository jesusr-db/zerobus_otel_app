# Technical Design Document: Observability Dashboard

## High-Level Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                    │
│  ┌────────────┬──────────────┬─────────────┬──────────────┐ │
│  │ Dependency │   Service    │   Service   │    Metrics   │ │
│  │    Map     │     List     │   Detail    │    Charts    │ │
│  │   (D3.js)  │   (Table)    │   (Panel)   │  (Recharts)  │ │
│  └────────────┴──────────────┴─────────────┴──────────────┘ │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        React Query (State + Auto-refresh)            │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API (30s polling)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (Python)                    │
│  ┌────────────┬──────────────┬─────────────┬──────────────┐ │
│  │ Dependency │   Metrics    │   Service   │  Warehouse   │ │
│  │   Router   │    Router    │   Router    │   Manager    │ │
│  └────────────┴──────────────┴─────────────┴──────────────┘ │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Databricks SDK (SQL Warehouse)               │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │ SQL Queries
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Databricks SQL Warehouse                        │
│                                                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │         jmr_demo.zerobus Database                  │     │
│  │  ┌──────────────────┬─────────────────────────┐   │     │
│  │  │ trace_assembled_ │  service_dependancy     │   │     │
│  │  │     silver       │                         │   │     │
│  │  └──────────────────┴─────────────────────────┘   │     │
│  │  ┌──────────────────┐                            │     │
│  │  │  metrics_silver  │                            │     │
│  │  └──────────────────┘                            │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Frontend
- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite (existing template)
- **State Management:** TanStack React Query v5 (existing)
- **UI Components:** shadcn/ui (existing) + custom components
- **Graph Visualization:** D3.js for dependency map
- **Charts:** Recharts for metrics visualization
- **Styling:** Tailwind CSS with dark theme

### Backend
- **Framework:** FastAPI (existing template)
- **Language:** Python 3.11+
- **Database Client:** Databricks SDK for SQL Warehouse
- **API Documentation:** OpenAPI/Swagger (auto-generated)
- **Package Manager:** uv (existing)

### Data Layer
- **Database:** Databricks Unity Catalog (`jmr_demo.zerobus`)
- **Query Engine:** SQL Warehouse (auto-detected)
- **Tables:**
  - `trace_assembled_silver` - trace/span data
  - `service_dependancy` - service relationships
  - `metrics_silver` - aggregated metrics

---

## Detailed Component Design

### Frontend Architecture

#### 1. Component Hierarchy
```
App
├── Layout (Dark Theme)
│   ├── Header (Time Range Selector + Auto-refresh indicator)
│   ├── Sidebar Navigation (Dashboard, Map, Services)
│   └── Main Content Area
│       ├── DashboardView
│       │   ├── ServiceHealthCards (grid of services)
│       │   └── MetricsSummary
│       ├── DependencyMapView
│       │   └── ServiceGraph (D3.js force-directed graph)
│       ├── ServiceListView
│       │   └── ServiceTable (sortable, filterable)
│       └── ServiceDetailPanel (slide-in overlay)
│           ├── ServiceHeader
│           ├── MetricsCharts (4 charts: latency, duration, errors, requests)
│           ├── DependencyList (inbound/outbound)
│           └── ErrorLogsList
```

#### 2. State Management Pattern
```typescript
// React Query for server state
const useServices = (timeRange: TimeRange) => {
  return useQuery({
    queryKey: ['services', timeRange],
    queryFn: () => apiClient.getServices(timeRange),
    refetchInterval: 30000, // 30s auto-refresh
  })
}

const useServiceDependencies = () => {
  return useQuery({
    queryKey: ['dependencies'],
    queryFn: () => apiClient.getDependencies(),
    refetchInterval: 30000,
  })
}

const useServiceMetrics = (serviceName: string, timeRange: TimeRange) => {
  return useQuery({
    queryKey: ['metrics', serviceName, timeRange],
    queryFn: () => apiClient.getServiceMetrics(serviceName, timeRange),
    refetchInterval: 30000,
    enabled: !!serviceName, // only fetch when service selected
  })
}
```

#### 3. D3.js Dependency Graph Implementation
```typescript
// Force-directed graph with health overlays
interface GraphNode {
  id: string; // service_name
  health: 'healthy' | 'warning' | 'critical';
  errorRate: number;
  requestCount: number;
}

interface GraphEdge {
  source: string; // source_service
  target: string; // target_service
  callCount: number;
}

// D3 force simulation with:
// - Node color based on health status
// - Edge thickness based on call_count
// - Pan/zoom with d3.zoom()
// - Click handlers for service detail panel
```

---

### Backend Architecture

#### 1. API Endpoints

##### Services API (`/api/services`)
```python
GET /api/services/list
  Query params: time_range (15m|1h|24h)
  Response: List[ServiceHealth]
    - service_name: str
    - current_latency_p50: float
    - current_latency_p95: float
    - current_latency_p99: float
    - avg_duration_ms: float
    - max_duration_ms: float
    - error_count: int
    - error_rate: float
    - request_count: int
    - requests_per_second: float
    - health_status: str  # healthy|warning|critical

GET /api/services/{service_name}/metrics
  Query params: time_range (15m|1h|24h)
  Response: ServiceMetricsDetail
    - current: MetricsSnapshot
    - trends: List[MetricsTimeSeries]  # time-bucketed data
    - baseline: MetricsSnapshot  # previous period comparison

GET /api/services/{service_name}/dependencies
  Response: ServiceDependencies
    - inbound: List[DependencyInfo]  # services calling this one
    - outbound: List[DependencyInfo]  # services this one calls
```

##### Dependencies API (`/api/dependencies`)
```python
GET /api/dependencies/graph
  Response: DependencyGraph
    - nodes: List[GraphNode]
    - edges: List[GraphEdge]
    
# Combines service_dependancy table with health metrics
# to create graph with health overlays
```

##### Warehouse API (`/api/warehouse`)
```python
GET /api/warehouse/info
  Response: WarehouseInfo
    - warehouse_id: str
    - warehouse_name: str
    - status: str
```

#### 2. Database Queries

##### Get Service Health Metrics
```sql
-- Query trace_assembled_silver for service metrics
WITH service_spans AS (
  SELECT 
    span.service_name,
    span.duration_ms,
    span.is_error,
    t.trace_start
  FROM jmr_demo.zerobus.trace_assembled_silver t
  LATERAL VIEW explode(span_details) AS span
  WHERE t.trace_start >= NOW() - INTERVAL {time_range}
),
service_metrics AS (
  SELECT
    service_name,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as latency_p50,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as latency_p99,
    AVG(duration_ms) as avg_duration,
    MAX(duration_ms) as max_duration,
    SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
    COUNT(*) as request_count
  FROM service_spans
  GROUP BY service_name
)
SELECT 
  service_name,
  latency_p50,
  latency_p95,
  latency_p99,
  avg_duration,
  max_duration,
  error_count,
  request_count,
  CAST(error_count AS FLOAT) / request_count as error_rate,
  request_count / ({time_range_seconds}) as requests_per_second,
  CASE 
    WHEN CAST(error_count AS FLOAT) / request_count > 0.05 THEN 'critical'
    WHEN CAST(error_count AS FLOAT) / request_count > 0.01 THEN 'warning'
    ELSE 'healthy'
  END as health_status
FROM service_metrics;
```

##### Get Service Dependencies with Health
```sql
-- Combine dependency graph with health metrics
WITH service_health AS (
  -- Same CTE as above to get health status
  SELECT service_name, health_status, error_rate
  FROM service_metrics
)
SELECT 
  d.source_service,
  d.target_service,
  d.call_count,
  s.health_status as source_health,
  t.health_status as target_health
FROM jmr_demo.zerobus.service_dependancy d
LEFT JOIN service_health s ON d.source_service = s.service_name
LEFT JOIN service_health t ON d.target_service = t.service_name;
```

##### Get Time Series Trends
```sql
-- Bucket metrics into time windows for trend charts
WITH service_spans AS (
  SELECT 
    span.service_name,
    span.duration_ms,
    span.is_error,
    date_trunc('minute', t.trace_start) as time_bucket
  FROM jmr_demo.zerobus.trace_assembled_silver t
  LATERAL VIEW explode(span_details) AS span
  WHERE t.trace_start >= NOW() - INTERVAL {time_range}
    AND span.service_name = {service_name}
)
SELECT
  time_bucket,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
  AVG(duration_ms) as avg_duration,
  SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
  COUNT(*) as request_count
FROM service_spans
GROUP BY time_bucket
ORDER BY time_bucket;
```

#### 3. Data Models

```python
# server/models/observability.py
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
    metrics: MetricsSnapshot

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
    baseline: MetricsSnapshot  # previous period for comparison

class DependencyInfo(BaseModel):
    service_name: str
    call_count: int
    health_status: str

class ServiceDependencies(BaseModel):
    service_name: str
    inbound: List[DependencyInfo]
    outbound: List[DependencyInfo]

class GraphNode(BaseModel):
    id: str  # service_name
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
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Days 1-2)

#### Backend Setup
1. **SQL Warehouse Integration**
   - Add `databricks-sdk` dependency
   - Create `WarehouseManager` service class
   - Implement auto-detect warehouse functionality
   - Test connection and query execution

2. **Data Models & API Structure**
   - Create Pydantic models in `server/models/observability.py`
   - Set up routers: `server/routers/services.py`, `server/routers/dependencies.py`
   - Implement basic query functions

3. **Core API Endpoints**
   - `GET /api/services/list` - basic service list
   - `GET /api/dependencies/graph` - dependency graph data
   - `GET /api/warehouse/info` - warehouse info

#### Frontend Setup
4. **UI Foundation**
   - Add D3.js and Recharts dependencies with `bun add`
   - Create dark theme configuration in Tailwind
   - Set up base layout with sidebar navigation
   - Create TypeScript types for API responses

5. **Basic Components**
   - `Layout` component with dark theme
   - `TimeRangeSelector` component (15m, 1h, 24h buttons)
   - Navigation shell

### Phase 2: Dependency Map (Days 3-4)

6. **Backend: Dependency Graph API**
   - Implement full query joining `service_dependancy` + health metrics
   - Add caching strategy for expensive queries
   - Optimize for large graphs (100+ services)

7. **Frontend: D3.js Graph Visualization**
   - Create `ServiceGraph` component with D3.js
   - Implement force-directed layout
   - Add node coloring based on health status
   - Add edge thickness based on call_count
   - Implement pan/zoom functionality
   - Add click handlers for service selection

8. **Service Selection State**
   - Create context for selected service
   - Wire up click → detail panel trigger

### Phase 3: Service Metrics (Days 5-6)

9. **Backend: Metrics APIs**
   - `GET /api/services/{service_name}/metrics` with time series
   - Implement percentile calculations (P50, P95, P99)
   - Add baseline comparison logic (current vs previous period)
   - Optimize queries with proper indexes

10. **Frontend: Metrics Display**
    - Create `ServiceDetailPanel` slide-in component
    - Add metric cards for current values
    - Implement Recharts line charts for trends
    - Add baseline comparison indicators
    - Wire up to React Query with 30s refresh

### Phase 4: Multi-View Layout (Days 7-8)

11. **Dashboard View**
    - Create `DashboardView` with service health grid
    - Add `ServiceHealthCard` components
    - Implement sorting and filtering

12. **Service List View**
    - Create `ServiceListView` with table
    - Add sortable columns (by error rate, latency, etc.)
    - Add search/filter functionality

13. **Auto-refresh & Polish**
    - Implement 30-second auto-refresh with React Query
    - Add loading states and error handling
    - Add refresh indicator in header
    - Performance optimization for large datasets

### Phase 5: Testing & Deployment (Days 9-10)

14. **Integration Testing**
    - Test all time ranges (15m, 1h, 24h)
    - Test with production data volume
    - Verify auto-refresh works correctly
    - Test error handling and edge cases

15. **Performance Optimization**
    - Profile SQL queries and optimize
    - Add query result caching if needed
    - Optimize React re-renders
    - Test with 100+ services

16. **Deployment**
    - Deploy to Databricks Apps
    - Monitor logs for errors
    - Verify SQL warehouse connectivity
    - Performance testing in production

---

## Data Flow

### Request Flow: Service List
```
User opens dashboard
  → Frontend: useServices() hook
  → React Query fetches /api/services/list?time_range=1h
  → Backend: ServicesRouter.get_services()
  → WarehouseManager.execute_query(service_health_sql)
  → SQL Warehouse: Query trace_assembled_silver
  → Backend: Parse results into ServiceHealth models
  → Frontend: Render service cards/table
  → Auto-refresh after 30s
```

### Request Flow: Dependency Graph
```
User clicks "Dependency Map"
  → Frontend: useDependencies() hook
  → React Query fetches /api/dependencies/graph
  → Backend: DependenciesRouter.get_graph()
  → WarehouseManager: Query service_dependancy + health
  → Backend: Build graph with nodes + edges
  → Frontend: D3.js renders force-directed graph
  → User clicks node → trigger service detail panel
```

### Request Flow: Service Details
```
User clicks service in graph
  → Frontend: setSelectedService(serviceName)
  → useServiceMetrics(serviceName, timeRange) hook
  → React Query fetches /api/services/{name}/metrics
  → Backend: Query time series + current + baseline
  → Frontend: Render detail panel with charts
  → Charts auto-refresh every 30s
```

---

## Security & Authentication

### Databricks OAuth
- App uses existing Databricks Apps OAuth integration
- User identity automatically passed to backend
- No custom auth needed (handled by platform)

### Data Access
- SQL queries use user's permissions automatically
- Unity Catalog enforces table-level access control
- No need for service accounts or PATs

---

## Performance Considerations

### Query Optimization
1. **Time Range Filtering:** Always filter by time range in WHERE clause
2. **Percentile Calculations:** Use approximate percentiles if exact not needed
3. **Aggregation Level:** Pre-aggregate by minute for trend charts
4. **Caching:** Consider caching dependency graph (changes infrequently)

### Frontend Optimization
1. **Virtual Scrolling:** For service list with 100+ services
2. **React.memo:** Memoize graph nodes to prevent unnecessary re-renders
3. **Code Splitting:** Lazy load D3.js and Recharts components
4. **Request Deduplication:** React Query handles this automatically

### Scaling Strategy
- If >500 services: Implement pagination or filtering
- If queries >5s: Add materialized views for common aggregations
- If >10 concurrent users: Consider query result caching layer

---

## Development Workflow

### Local Development
1. Run `./watch.sh` to start dev servers
2. Frontend: http://localhost:5173
3. Backend: http://localhost:8000
4. Auto-reload on file changes
5. Use FastAPI docs: http://localhost:8000/docs for API testing

### Testing Strategy
1. **Backend:** Use FastAPI test client to test endpoints
2. **Frontend:** Manual testing with Playwright
3. **Integration:** Test with real SQL warehouse and data
4. **Performance:** Test with production-scale data

### Deployment Process
1. Commit changes to git
2. Run `./fix.sh` to format code
3. Run `./deploy.sh` to deploy to Databricks Apps
4. Monitor logs with `dba_logz.py` for errors
5. Verify app at production URL

---

## Dependencies & Libraries

### Backend (Python)
```toml
# Add to pyproject.toml
databricks-sdk = "^0.40.0"  # SQL Warehouse + Unity Catalog
fastapi = "^0.115.0"  # Already in template
pydantic = "^2.0.0"  # Already in template
```

### Frontend (TypeScript)
```bash
# Install with: bun add <package>
bun add d3@^7.9.0
bun add @types/d3@^7.9.0
bun add recharts@^2.15.0
```

Existing dependencies (already in template):
- react@^18.3.1
- @tanstack/react-query@^5.82.0
- tailwindcss@^3.4.0
- shadcn/ui components

---

## Risks & Mitigations

### Risk: Slow Query Performance
**Mitigation:**
- Add indexes on trace_start, service_name columns
- Use approximate percentiles if exact not needed
- Implement query timeouts
- Add caching layer if needed

### Risk: Large Dependency Graphs (>500 services)
**Mitigation:**
- Implement graph filtering by health status
- Add search to focus on specific services
- Consider hierarchical clustering for large graphs
- Pagination or virtualization for service lists

### Risk: SQL Warehouse Unavailable
**Mitigation:**
- Add error handling with user-friendly messages
- Implement retry logic with exponential backoff
- Show cached data if available
- Health check endpoint to verify warehouse status

### Risk: High Query Frequency (30s refresh)
**Mitigation:**
- Monitor SQL warehouse usage and scale if needed
- Implement query result caching (5-10s TTL)
- Consider increasing refresh interval to 60s if needed
- Use efficient queries with proper WHERE clauses

---

## Future Enhancements (Post-MVP)

1. **Advanced Filtering**
   - Filter graph by service name regex
   - Filter by error rate threshold
   - Filter by request volume

2. **Custom Time Ranges**
   - Date/time picker for custom ranges
   - Quick presets (last 7 days, last 30 days)

3. **Alerting Integration**
   - Define threshold rules for services
   - Email/Slack notifications on threshold breach
   - Alert history and management

4. **Log Integration**
   - Show recent error logs for services
   - Link to full log viewer
   - Log search and filtering

5. **Anomaly Detection**
   - ML-based anomaly detection on metrics
   - Highlight unusual patterns
   - Root cause analysis suggestions

6. **Export Capabilities**
   - Export graphs as PNG/SVG
   - Export metrics as CSV
   - Share dashboard snapshots

7. **Service Comparison**
   - Compare metrics across multiple services
   - Side-by-side comparison view
   - Performance benchmarking
