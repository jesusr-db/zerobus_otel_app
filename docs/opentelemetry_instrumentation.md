# OpenTelemetry Instrumentation Documentation

## Overview

This application implements comprehensive OpenTelemetry instrumentation to capture **traces, metrics, and logs** from a FastAPI backend application. All telemetry data is exported to Databricks Unity Catalog tables via OTLP (OpenTelemetry Protocol) over HTTP.

---

## Current Instrumentation Architecture

### 1. **Core Components**

#### **Tracing Setup** (`server/tracing.py`)
- **TracerProvider**: Configured with service name `o11y-app`
- **BatchSpanProcessor**: Exports spans every 1 second (optimized from default 5s)
- **OTLPSpanExporter**: Sends traces to `{DATABRICKS_HOST}/api/2.0/otel/v1/traces`
- **Resource Attributes**: Service identification metadata

#### **Metrics Setup** (`server/tracing.py`)
- **MeterProvider**: Configured with periodic metric reader
- **PeriodicExportingMetricReader**: Exports metrics every 10 seconds
- **OTLPMetricExporter**: Sends metrics to `{DATABRICKS_HOST}/api/2.0/otel/v1/metrics`
- **SystemMetricsInstrumentor**: Auto-captures CPU, memory, disk, network metrics

#### **Logging Setup** (`server/tracing.py`)
- **LoggerProvider**: Configured with batch log processor
- **BatchLogRecordProcessor**: Batches and exports log records
- **OTLPLogExporter**: Sends logs to `{DATABRICKS_HOST}/api/2.0/otel/v1/logs`
- **LoggingInstrumentor**: Injects trace context into application logs
- **LoggingHandler**: Bridges Python logging to OpenTelemetry logs

### 2. **Application Integration** (`server/app.py`)

#### **Automatic Instrumentation**
```python
FastAPIInstrumentor.instrument_app(app)
```
- Auto-captures HTTP requests/responses for FastAPI endpoints
- Records request duration, status codes, HTTP methods
- Creates parent spans for each incoming request

#### **Custom Middleware Instrumentation**
```python
@app.middleware('http')
async def trace_middleware(request: Request, call_next):
```
- Creates manual spans for every HTTP request
- Captures attributes: `http.method`, `http.url`, `http.status_code`
- Provides redundancy if FastAPIInstrumentor fails to capture spans

#### **Logging Integration**
```python
format='%(asctime)s [%(levelname)s] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] %(message)s'
```
- Injects `trace_id` and `span_id` into log messages
- Enables correlation between logs and distributed traces

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐       ┌──────────────────┐            │
│  │  HTTP Request    │──────▶│  FastAPI         │            │
│  │  (User/Client)   │       │  Instrumentor    │            │
│  └──────────────────┘       └──────────────────┘            │
│                                      │                        │
│                                      ▼                        │
│                          ┌──────────────────────┐            │
│                          │  Custom Middleware   │            │
│                          │  (trace_middleware)  │            │
│                          └──────────────────────┘            │
│                                      │                        │
│                                      ▼                        │
│                          ┌──────────────────────┐            │
│                          │   Application Code   │            │
│                          │  (Routers/Services)  │            │
│                          └──────────────────────┘            │
│                                      │                        │
│                                      ▼                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         OpenTelemetry SDK Components                  │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  TracerProvider  │  MeterProvider  │  LoggerProvider │   │
│  └──────────────────────────────────────────────────────┘   │
│                │                │                │           │
│                ▼                ▼                ▼           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Batch Processors (1s, 10s intervals)        │   │
│  └──────────────────────────────────────────────────────┘   │
│                │                │                │           │
│                ▼                ▼                ▼           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         OTLP Exporters (HTTP/Protobuf)               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               Databricks OTLP Receiver                       │
│          /api/2.0/otel/v1/{traces,metrics,logs}              │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                Unity Catalog Tables                          │
├─────────────────────────────────────────────────────────────┤
│  - {catalog}.{schema}.otel_spans    (Traces)                │
│  - {catalog}.{schema}.otel_metrics  (Metrics)                │
│  - {catalog}.{schema}.otel_logs     (Logs)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## What is Currently Instrumented

### ✅ **Captured Automatically**

1. **HTTP Request/Response Metrics**
   - Request method, URL path, status code
   - Request duration (latency)
   - HTTP headers (sanitized)

2. **System Metrics** (via `SystemMetricsInstrumentor`)
   - CPU usage (user, system, idle percentages)
   - Memory usage (available, used, total)
   - Disk I/O (read/write bytes, operations)
   - Network I/O (bytes sent/received)

3. **Application Logs**
   - All Python `logging` statements
   - Correlated with trace context (trace_id, span_id)
   - Log level, timestamp, message

4. **Distributed Traces**
   - End-to-end request flow through FastAPI
   - Parent-child span relationships
   - Request timing and latency breakdown

---

## Telemetry Blind Spots & Missing Coverage

### ❌ **What is NOT Currently Instrumented**

#### 1. **Database Query Performance**
**Location**: `server/services/warehouse_manager.py`

**Current State**:
```python
def execute_query(self, query: str) -> List[Dict[str, Any]]:
    # No span created for query execution
    statement = self.client.statement_execution.execute_statement(...)
```

**Blind Spot**:
- SQL query execution time not captured
- Query parameters/content not logged
- Database connection pool metrics missing
- Query result size not tracked

**Impact**: Cannot identify slow queries or database bottlenecks

---

#### 2. **Databricks SDK Operations**
**Location**: `server/services/warehouse_manager.py`

**Current State**:
```python
def _auto_detect_warehouse(self) -> str:
    # No instrumentation for warehouse discovery
    warehouses = list(self.client.warehouses.list())
```

**Blind Spot**:
- Warehouse API call latency not tracked
- Authentication failures not captured
- API rate limiting not visible
- SDK initialization time not measured

**Impact**: Cannot diagnose Databricks API performance issues

---

#### 3. **Business Logic Spans**
**Location**: `server/routers/services.py`, `server/routers/traces.py`

**Current State**:
```python
async def get_services(request: Request, time_range: TimeRange):
    # No custom span for business logic
    warehouse_manager = WarehouseManager(user_token=user_token)
    query = f"SELECT ... FROM ..."  # Complex query generation
    results = warehouse_manager.execute_query(query)
```

**Blind Spot**:
- Query construction time not measured
- Data transformation/aggregation not traced
- Service-specific metrics not captured
- Business operations not isolated in traces

**Impact**: Cannot identify which part of request processing is slow

---

#### 4. **External HTTP Calls**
**Location**: Not yet present, but likely needed for external integrations

**Blind Spot**:
- No instrumentation for `requests` or `httpx` libraries
- External API call latency not tracked
- Retry logic not visible in traces

**Impact**: Cannot diagnose external service dependencies

---

#### 5. **Custom Application Metrics**
**Location**: Throughout application

**Blind Spot**:
- No business metrics (e.g., queries processed per minute)
- No user behavior metrics (e.g., most accessed services)
- No data volume metrics (e.g., rows returned per query)
- No error rate tracking by endpoint

**Impact**: Cannot measure business KPIs or SLOs

---

#### 6. **Error Details and Stack Traces**
**Location**: Exception handling throughout application

**Current State**:
```python
except Exception as e:
    logger.error(f"Query execution error: {e}", exc_info=True)
    raise
```

**Blind Spot**:
- Stack traces not attached to spans
- Error categorization not implemented
- Exception types not recorded as span attributes
- User-facing vs internal errors not distinguished

**Impact**: Cannot perform detailed error analysis in traces

---

#### 7. **Query Result Caching**
**Location**: Not implemented

**Blind Spot**:
- Cache hit/miss rates not tracked
- Cache performance not measured
- No instrumentation for potential caching layer

**Impact**: Cannot optimize caching strategy

---

## Recommended Instrumentation Additions

### 🎯 **High Priority: Database Query Instrumentation**

**Implementation**:
```python
# server/services/warehouse_manager.py
from opentelemetry import trace

class WarehouseManager:
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(
            "databricks.query.execute",
            attributes={
                "db.system": "databricks",
                "db.operation": "SELECT",  # Parse from query
                "db.warehouse.id": self.get_warehouse_id(),
            }
        ) as span:
            try:
                warehouse_id = self.get_warehouse_id()
                logger.info(f"Executing query on warehouse: {warehouse_id}")
                
                statement = self.client.statement_execution.execute_statement(
                    warehouse_id=warehouse_id,
                    statement=query,
                    wait_timeout="50s"
                )
                
                # Add result metrics to span
                row_count = len(statement.result.data_array) if statement.result else 0
                span.set_attribute("db.result.rows", row_count)
                span.set_attribute("db.statement.duration_ms", 
                                   statement.status.execution_duration_ms or 0)
                
                if statement.status.state != StatementState.SUCCEEDED:
                    span.set_status(Status(StatusCode.ERROR))
                    span.set_attribute("db.error", statement.status.error.message)
                    error_message = statement.status.error.message if statement.status.error else "Unknown error"
                    logger.error(f"Query failed: {error_message}")
                    raise RuntimeError(f"Query failed: {error_message}")
                
                return self._process_results(statement)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
```

**Benefits**:
- Track slow queries in distributed traces
- Identify database performance bottlenecks
- Measure query execution time separately from network overhead

---

### 🎯 **High Priority: Business Logic Spans**

**Implementation**:
```python
# server/routers/services.py
from opentelemetry import trace

@router.get("/list")
async def get_services(request: Request, time_range: TimeRange):
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span("services.list") as span:
        span.set_attribute("time_range", time_range)
        
        user_token = request.headers.get("X-Forwarded-Access-Token")
        warehouse_manager = WarehouseManager(user_token=user_token)
        interval, seconds = get_time_range_interval(time_range)
        
        with tracer.start_as_current_span("services.query.construct"):
            query = f"""..."""  # Query construction
        
        with tracer.start_as_current_span("services.data.fetch"):
            results = warehouse_manager.execute_query(query)
        
        with tracer.start_as_current_span("services.data.transform"):
            services = [ServiceHealth(**row) for row in results]
            span.set_attribute("services.count", len(services))
        
        return services
```

**Benefits**:
- Isolate which phase of request processing is slow
- Measure data transformation overhead
- Track result cardinality per request

---

### 🎯 **Medium Priority: Custom Application Metrics**

**Implementation**:
```python
# server/routers/services.py
from opentelemetry import metrics

meter = metrics.get_meter(__name__)
query_counter = meter.create_counter(
    "services.queries.total",
    description="Total number of service list queries",
    unit="1"
)
query_duration = meter.create_histogram(
    "services.query.duration",
    description="Service query duration",
    unit="ms"
)
result_size = meter.create_histogram(
    "services.result.size",
    description="Number of services returned",
    unit="1"
)

@router.get("/list")
async def get_services(request: Request, time_range: TimeRange):
    start_time = time.time()
    
    try:
        # ... existing code ...
        results = warehouse_manager.execute_query(query)
        
        # Record metrics
        query_counter.add(1, {"time_range": time_range, "status": "success"})
        result_size.record(len(results), {"time_range": time_range})
        
        return [ServiceHealth(**row) for row in results]
    finally:
        duration_ms = (time.time() - start_time) * 1000
        query_duration.record(duration_ms, {"time_range": time_range})
```

**Benefits**:
- Track query patterns and usage
- Measure SLOs (e.g., P95 latency < 500ms)
- Alert on anomalies (e.g., sudden drop in query rate)

---

### 🎯 **Medium Priority: Error Categorization**

**Implementation**:
```python
# server/services/warehouse_manager.py
from opentelemetry.trace import Status, StatusCode

def execute_query(self, query: str) -> List[Dict[str, Any]]:
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("databricks.query.execute") as span:
        try:
            # ... execution logic ...
        except ValueError as e:
            # User error (bad input)
            span.set_status(Status(StatusCode.ERROR))
            span.set_attribute("error.type", "user_error")
            span.set_attribute("error.message", str(e))
            span.record_exception(e)
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            # System error (database failure)
            span.set_status(Status(StatusCode.ERROR))
            span.set_attribute("error.type", "system_error")
            span.set_attribute("error.message", str(e))
            span.record_exception(e)
            raise HTTPException(status_code=500, detail="Internal server error")
```

**Benefits**:
- Distinguish between user errors and system failures
- Track error rates by category
- Attach full stack traces to spans for debugging

---

### 🎯 **Low Priority: HTTP Client Instrumentation**

**Implementation**:
```python
# If using requests or httpx for external calls
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# In setup_tracing()
RequestsInstrumentor().instrument()
HTTPXClientInstrumentor().instrument()
```

**Benefits**:
- Auto-capture external API call latency
- Track external service dependencies
- Measure impact of external services on overall latency

---

## Configuration

### Environment Variables
```bash
# Required for OTLP export
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
OTEL_TOKEN=dapi...  # Separate token for OTLP authentication
OTEL_TRACES_TABLE=catalog.schema.otel_spans
OTEL_METRICS_TABLE=catalog.schema.otel_metrics
OTEL_LOGS_TABLE=catalog.schema.otel_logs
```

### Tuning Parameters
- **Trace export interval**: 1 second (line 76, `tracing.py`)
- **Metric export interval**: 10 seconds (line 87, `tracing.py`)
- **Batch size**: 512 spans (line 77, `tracing.py`)
- **Queue size**: 2048 spans (line 75, `tracing.py`)

---

## Summary

### Current Coverage
- ✅ HTTP request/response tracing
- ✅ System resource metrics
- ✅ Application logging with trace correlation
- ✅ Basic distributed tracing

### Major Gaps
- ❌ Database query performance
- ❌ Business logic breakdown
- ❌ Custom application metrics
- ❌ Error categorization
- ❌ SDK operation tracing

### Quick Wins
1. Add database query spans (highest impact)
2. Add business logic spans (isolate bottlenecks)
3. Implement custom metrics (measure SLOs)
4. Categorize errors (improve debugging)
