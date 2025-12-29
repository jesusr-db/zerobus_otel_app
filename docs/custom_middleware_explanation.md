# Custom OpenTelemetry Middleware - Detailed Explanation

## Overview

The custom middleware (`trace_middleware`) provides **manual span creation** for every HTTP request as a backup/verification mechanism for the automatic `FastAPIInstrumentor`. This documentation explains why it exists, how it works, and its relationship to the automatic instrumentation.

---

## The Code

```python
# server/app.py (lines 68-77)

@app.middleware('http')
async def trace_middleware(request: Request, call_next):
  tracer = trace.get_tracer(__name__)
  with tracer.start_as_current_span(f'{request.method} {request.url.path}') as span:
    span.set_attribute('http.method', request.method)
    span.set_attribute('http.url', str(request.url))
    logger.debug(f'Created span for {request.method} {request.url.path}')
    response = await call_next(request)
    span.set_attribute('http.status_code', response.status_code)
    return response
```

---

## Why This Exists: Dual Instrumentation Strategy

### The Problem It Solves

During initial implementation, we discovered that `FastAPIInstrumentor.instrument_app(app)` was **not creating spans for HTTP requests**, even though the instrumentation appeared to be configured correctly. This custom middleware was added as:

1. **Debugging tool** - Verify that the OpenTelemetry SDK is working and can create spans
2. **Redundancy** - Ensure HTTP requests are traced even if automatic instrumentation fails
3. **Customization** - Provide control over span naming and attributes

### The Result

With this dual approach:
- If `FastAPIInstrumentor` works → Two layers of spans (nested parent-child relationship)
- If `FastAPIInstrumentor` fails → Custom middleware ensures at least one span per request

---

## How It Works: Step-by-Step

### 1. **Middleware Registration**

```python
@app.middleware('http')
async def trace_middleware(request: Request, call_next):
```

**What this does:**
- Registers a middleware function that intercepts **every HTTP request**
- Runs **before** the request reaches route handlers
- Executes in the **FastAPI middleware stack order**

**Middleware execution order:**
```
Incoming Request
    ↓
[CORS Middleware]  ← Registered after (executes first)
    ↓
[trace_middleware] ← Our custom middleware (executes second)
    ↓
[FastAPIInstrumentor] ← Automatic instrumentation (executes third)
    ↓
[Route Handler] ← Your application code
    ↓
Response
```

---

### 2. **Tracer Acquisition**

```python
tracer = trace.get_tracer(__name__)
```

**What this does:**
- Gets a `Tracer` instance from the global `TracerProvider` (configured in `setup_tracing()`)
- The tracer is namespaced to `server.app` (from `__name__`)
- This is the standard OpenTelemetry pattern for creating spans

**Why this pattern:**
- Decouples span creation from tracer configuration
- Allows runtime configuration changes without code modification
- Enables tracing to be disabled globally without changing application code

---

### 3. **Span Creation (Context Manager)**

```python
with tracer.start_as_current_span(f'{request.method} {request.url.path}') as span:
```

**What this does:**
- Creates a **new span** with name like `"GET /api/services/list"`
- Sets the span as the **current active span** (for child span propagation)
- Automatically handles span **start time** and **end time**
- Ensures span is **closed** even if exceptions occur (via context manager)

**Key behavior:**
- If a parent span exists (from `FastAPIInstrumentor`), this becomes a **child span**
- If no parent span exists, this becomes the **root span** of the trace
- The context manager guarantees the span is finished when the block exits

---

### 4. **Span Attributes - Request Phase**

```python
span.set_attribute('http.method', request.method)
span.set_attribute('http.url', str(request.url))
```

**What this does:**
- Adds **semantic attributes** to the span following OpenTelemetry conventions
- `http.method`: HTTP verb (GET, POST, PUT, DELETE, etc.)
- `http.url`: Full URL including query parameters

**Why semantic conventions matter:**
- Enables standardized queries across different services
- Tools like Jaeger/Zipkin can auto-recognize and visualize these attributes
- Allows filtering: "Show all POST requests" or "Show all requests to /api/services"

**Example span attributes:**
```json
{
  "http.method": "GET",
  "http.url": "http://localhost:8000/api/services/list?time_range=1h",
  "http.status_code": 200  // Added after response
}
```

---

### 5. **Request Processing**

```python
logger.debug(f'Created span for {request.method} {request.url.path}')
response = await call_next(request)
```

**What this does:**
- Logs span creation for debugging (visible in console/logs)
- `call_next(request)` invokes the **next middleware or route handler**
- This is where the actual application logic executes
- The span remains **active** throughout request processing

**Key insight:**
- Any spans created during `call_next()` will be **child spans** of this span
- This creates the trace hierarchy:
  ```
  trace_middleware span
  ├── FastAPIInstrumentor span (if present)
  │   ├── Route handler span (if manually added)
  │   ├── Database query span (if added)
  │   └── Business logic span (if added)
  ```

---

### 6. **Span Attributes - Response Phase**

```python
span.set_attribute('http.status_code', response.status_code)
return response
```

**What this does:**
- Captures the **HTTP status code** after request processing completes
- Adds it to the span before the span closes
- Returns the response to the client

**Why status code is important:**
- Enables error analysis: "Show all 5xx errors"
- Calculates error rates: "What % of requests failed?"
- Identifies endpoints with problems: "Which endpoint has most 500s?"

**Span lifecycle:**
```
1. Span created (start_time recorded)
2. Attributes set: http.method, http.url
3. Request processed via call_next()
4. Response received
5. Attribute set: http.status_code
6. Context manager exits → span.end() called automatically
7. Span exported to OTLP endpoint (after 1 second batch interval)
```

---

## Relationship to FastAPIInstrumentor

### Automatic Instrumentation (FastAPIInstrumentor)

```python
FastAPIInstrumentor.instrument_app(app)
```

**What it does automatically:**
- Creates spans for **every HTTP request/response**
- Captures standard HTTP attributes (method, URL, status, headers)
- Records exceptions if route handler raises errors
- Integrates with FastAPI's dependency injection and middleware system

**Advantages:**
- Zero-code instrumentation
- Follows OpenTelemetry semantic conventions
- Battle-tested and maintained by the community

**Why it might not work:**
- Initialization order issues (tracer provider not set before instrumentation)
- Middleware conflicts (other middleware interfering)
- Configuration issues (environment variables not loaded)

---

### Custom Middleware (trace_middleware)

**What it does:**
- **Redundantly** creates spans for HTTP requests
- Provides **explicit control** over span naming and attributes
- Serves as **verification** that OpenTelemetry SDK is working

**Advantages:**
- Guaranteed to work if TracerProvider is configured
- Full control over span attributes
- Easy to debug and customize

**Disadvantages:**
- Duplicates functionality of FastAPIInstrumentor
- Creates nested spans if both work simultaneously
- Requires manual maintenance

---

## Span Hierarchy When Both Work

### Dual Instrumentation Result

```
Root Trace (trace_id: abc123)
│
└─ trace_middleware span
   │ name: "GET /api/services/list"
   │ attributes: {http.method, http.url, http.status_code}
   │ duration: 245ms
   │
   └─ FastAPIInstrumentor span
      │ name: "GET /api/services/list"
      │ attributes: {http.method, http.url, http.status_code, http.route, ...}
      │ duration: 243ms
      │
      └─ [Route handler execution]
         └─ [Business logic, database queries, etc.]
```

**Key observations:**
1. **Two spans** with similar names (potential duplication)
2. `FastAPIInstrumentor` span is **child** of `trace_middleware` span
3. Both measure nearly the same duration (slight overhead difference)
4. This is **intentional redundancy** for reliability

---

## Best Practices & Recommendations

### Current State: Debugging/Development Mode

The dual instrumentation is useful for:
- **Verifying** OpenTelemetry is working
- **Debugging** why FastAPIInstrumentor might not create spans
- **Testing** custom span attributes

### Production Recommendation: Choose One

**Option 1: Remove Custom Middleware (Preferred)**
```python
# Comment out or remove the custom middleware
# @app.middleware('http')
# async def trace_middleware(request: Request, call_next):
#     ...
```

**Pros:**
- Standard OpenTelemetry approach
- Less overhead (one span per request instead of two)
- Automatic updates when FastAPIInstrumentor improves

**When to use:**
- FastAPIInstrumentor reliably creates spans
- No need for custom span attributes

---

**Option 2: Keep Custom Middleware, Remove FastAPIInstrumentor**
```python
# Remove this line:
# FastAPIInstrumentor.instrument_app(app)

# Keep custom middleware
@app.middleware('http')
async def trace_middleware(request: Request, call_next):
    # ... existing code
```

**Pros:**
- Full control over span creation
- Can customize span names (e.g., use route patterns instead of paths)
- Can add custom attributes specific to your application

**When to use:**
- Need custom span naming conventions
- FastAPIInstrumentor doesn't meet requirements
- Want explicit control over instrumentation

---

**Option 3: Enhance Custom Middleware (Advanced)**
```python
@app.middleware('http')
async def trace_middleware(request: Request, call_next):
  tracer = trace.get_tracer(__name__)
  
  # Use route pattern instead of path
  route_pattern = request.scope.get('route')
  span_name = f"{request.method} {route_pattern.path if route_pattern else request.url.path}"
  
  with tracer.start_as_current_span(span_name) as span:
    # Standard HTTP attributes
    span.set_attribute('http.method', request.method)
    span.set_attribute('http.url', str(request.url))
    span.set_attribute('http.scheme', request.url.scheme)
    span.set_attribute('http.target', request.url.path)
    
    # Custom application attributes
    span.set_attribute('user.token.present', bool(request.headers.get('X-Forwarded-Access-Token')))
    span.set_attribute('app.version', app.version)
    
    try:
      response = await call_next(request)
      span.set_attribute('http.status_code', response.status_code)
      
      # Mark errors in span status
      if response.status_code >= 500:
        span.set_status(Status(StatusCode.ERROR, "Server error"))
      elif response.status_code >= 400:
        span.set_status(Status(StatusCode.ERROR, "Client error"))
      
      return response
    except Exception as e:
      span.record_exception(e)
      span.set_status(Status(StatusCode.ERROR, str(e)))
      raise
```

**Enhancements:**
- Uses **route pattern** instead of actual path (e.g., `/api/user/{id}` instead of `/api/user/123`)
- Adds **custom attributes** specific to your application
- Properly **marks errors** in span status
- **Records exceptions** with stack traces

---

## Key Concepts Explained

### 1. **Context Propagation**

```python
with tracer.start_as_current_span(...) as span:
```

**What "current span" means:**
- OpenTelemetry uses **context propagation** to maintain parent-child relationships
- When you create a span as "current," any spans created within that scope become children
- This happens automatically via Python's `contextvars` module

**Example:**
```python
with tracer.start_as_current_span("parent"):
    # This span is the "current" span
    
    with tracer.start_as_current_span("child"):
        # This automatically becomes a child of "parent"
        pass
```

---

### 2. **Span Lifecycle Management**

**Manual approach (error-prone):**
```python
span = tracer.start_span("my-span")
try:
    # Do work
    span.set_attribute("result", "success")
finally:
    span.end()  # MUST call .end() or span is never exported!
```

**Context manager approach (recommended):**
```python
with tracer.start_as_current_span("my-span") as span:
    # Do work
    span.set_attribute("result", "success")
    # span.end() called automatically, even if exception occurs
```

---

### 3. **Semantic Attributes**

OpenTelemetry defines **semantic conventions** for common attributes:

**HTTP attributes:**
- `http.method` - HTTP verb
- `http.url` - Full URL
- `http.status_code` - Response status
- `http.route` - Route pattern (e.g., `/users/{id}`)
- `http.target` - Path and query string

**Database attributes:**
- `db.system` - Database type (e.g., "databricks", "postgresql")
- `db.operation` - Operation type (e.g., "SELECT", "INSERT")
- `db.statement` - SQL query (sanitized)

**Custom attributes:**
- Any key-value pair you define
- Use namespaces: `app.user.id`, `custom.feature.flag`

---

## Debugging Tips

### Verify Custom Middleware is Working

**Check logs for:**
```
DEBUG:server.app:Created span for GET /api/services/list
```

### Verify Spans are Being Created

**Enable debug logging:**
```python
logging.getLogger('opentelemetry.sdk.trace').setLevel(logging.DEBUG)
```

**Look for:**
```
DEBUG:opentelemetry.sdk.trace:Span started: GET /api/services/list
DEBUG:opentelemetry.sdk.trace:Span ended: GET /api/services/list
```

### Verify Spans are Being Exported

**Look for:**
```
DEBUG:opentelemetry.exporter:Exporting 1 spans to http://...
```

---

## Summary

The custom middleware serves as:
1. **Backup instrumentation** if FastAPIInstrumentor fails
2. **Debugging tool** to verify OpenTelemetry is working
3. **Foundation** for custom instrumentation if needed

**Current state:** Both automatic and custom instrumentation are active (dual layer)

**Recommendation:** Once FastAPIInstrumentor is confirmed working, remove custom middleware to avoid duplication.
