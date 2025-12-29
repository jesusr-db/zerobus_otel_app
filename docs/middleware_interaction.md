# Custom Middleware vs FastAPIInstrumentor Interaction

## The Two Instrumentation Layers

```python
# Line 63: Automatic instrumentation
FastAPIInstrumentor.instrument_app(app)

# Lines 68-77: Custom middleware
@app.middleware('http')
async def trace_middleware(request: Request, call_next):
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(f'{request.method} {request.url.path}') as span:
        span.set_attribute('http.method', request.method)
        span.set_attribute('http.url', str(request.url))
        response = await call_next(request)
        span.set_attribute('http.status_code', response.status_code)
        return response
```

---

## Execution Flow: Request Processing Order

When a request arrives at `GET /api/services/list`, here's the **exact execution sequence**:

### 1. **CORS Middleware Executes First** (line 80)

```
Incoming HTTP Request
    ↓
┌─────────────────────────────────────┐
│   CORSMiddleware                    │
│   - Check origin                    │
│   - Add CORS headers                │
└─────────────────────────────────────┘
    ↓
```

**Why CORS is first:**
- Registered with `app.add_middleware()` **after** custom middleware
- FastAPI processes middleware in **reverse registration order**
- CORS needs to run first to handle preflight requests

---

### 2. **Custom Middleware Creates Parent Span** (line 68)

```
    ↓
┌─────────────────────────────────────┐
│   trace_middleware                  │
│                                     │
│   tracer.start_as_current_span()   │  ← Creates PARENT span
│   - Name: "GET /api/services/list" │
│   - Attributes: http.method, url   │
│   - Sets as CURRENT span            │
└─────────────────────────────────────┘
    ↓
    [Span is ACTIVE in context]
    ↓
```

**Key behavior:**
- `start_as_current_span()` stores the span in **thread-local context** (`contextvars`)
- This span becomes the **parent** for any child spans created downstream
- The `with` block keeps the span **active** until `call_next()` completes

---

### 3. **FastAPIInstrumentor Creates Child Span** (automatic)

```
    ↓
    await call_next(request)  ← Invokes next middleware
    ↓
┌─────────────────────────────────────┐
│   FastAPIInstrumentor               │
│   (injected automatically)          │
│                                     │
│   tracer.start_as_current_span()   │  ← Creates CHILD span
│   - Name: "GET /api/services/list" │
│   - Parent: trace_middleware span  │  ← Links to parent!
│   - Attributes: http.*, fastapi.*  │
└─────────────────────────────────────┘
    ↓
```

**How parent-child relationship works:**

```python
# Custom middleware (parent)
with tracer.start_as_current_span("parent") as parent_span:
    # Sets parent_span as "current" in context
    
    # FastAPIInstrumentor (child) - happens inside call_next()
    # Automatically reads "current" span from context
    with tracer.start_as_current_span("child") as child_span:
        # child_span.parent = parent_span (automatic!)
        pass
```

**Context propagation mechanism:**
- Python's `contextvars` module stores the "current span"
- When `start_as_current_span()` is called, it checks the context
- If a span exists in context → new span becomes its child
- If no span in context → new span becomes root of trace

---

### 4. **Route Handler Executes**

```
    ↓
┌─────────────────────────────────────┐
│   Route Handler                     │
│   async def get_services(...)       │
│                                     │
│   - Create WarehouseManager         │
│   - Execute SQL query               │
│   - Transform results               │
└─────────────────────────────────────┘
    ↓
    [Returns response]
```

**If route handler creates spans:**

```python
@router.get("/list")
async def get_services(request: Request):
    tracer = trace.get_tracer(__name__)
    
    # This becomes a child of FastAPIInstrumentor span
    with tracer.start_as_current_span("get_services.logic"):
        # Your code here
        pass
```

---

### 5. **Response Flows Back Through Middleware Stack**

```
    ↓
┌─────────────────────────────────────┐
│   FastAPIInstrumentor               │
│   - Adds http.status_code           │
│   - Closes child span               │  ← Child span ends
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│   trace_middleware                  │
│   - Adds http.status_code           │
│   - Closes parent span              │  ← Parent span ends
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│   CORSMiddleware                    │
│   - Returns response with headers   │
└─────────────────────────────────────┘
    ↓
HTTP Response to Client
```

---

## Resulting Trace Structure

The final trace in Databricks/Jaeger looks like this:

```
Trace ID: abc123xyz (unique per request)
│
└─ Span: GET /api/services/list                    [245ms] ← trace_middleware (PARENT)
   │ service: o11y-app
   │ trace_id: abc123xyz
   │ span_id: span001
   │ parent_id: null  (root span)
   │ attributes:
   │   - http.method: GET
   │   - http.url: http://localhost:8000/api/services/list?time_range=1h
   │   - http.status_code: 200
   │
   └─ Span: GET /api/services/list                 [243ms] ← FastAPIInstrumentor (CHILD)
      │ service: o11y-app
      │ trace_id: abc123xyz
      │ span_id: span002
      │ parent_id: span001  ← Links to parent!
      │ attributes:
      │   - http.method: GET
      │   - http.url: http://localhost:8000/api/services/list?time_range=1h
      │   - http.status_code: 200
      │   - http.route: /api/services/list
      │   - http.target: /api/services/list?time_range=1h
      │   - fastapi.route_path: /api/services/list
      │
      └─ (Route handler spans would go here)
```

---

## Why You See Nested Duplicate Spans

### Visual Representation

**In a trace viewer (Jaeger/Databricks):**

```
Timeline:  0ms ──────────────────────────────────────► 245ms

┌─────────────────────────────────────────────────────────┐
│ GET /api/services/list (trace_middleware)               │ 245ms
│ ┌─────────────────────────────────────────────────────┐ │
│ │ GET /api/services/list (FastAPIInstrumentor)        │ │ 243ms
│ │                                                      │ │
│ │    [Route handler execution]                        │ │
│ │                                                      │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**The 2ms difference:**
- Parent span includes middleware processing overhead
- Child span only measures handler execution
- Small difference indicates minimal middleware overhead

---

## Code Analysis: Context Propagation

### Custom Middleware (Creates Context)

```python
@app.middleware('http')
async def trace_middleware(request: Request, call_next):
    tracer = trace.get_tracer(__name__)
    
    # Creates span AND sets it as current context
    with tracer.start_as_current_span(...) as span:
        # ↓ At this point, span is stored in contextvars
        
        # This invokes FastAPIInstrumentor
        response = await call_next(request)
        
        # ↓ Context still has our span active
        return response
```

**What happens inside `start_as_current_span()`:**

```python
# Simplified OpenTelemetry SDK code
def start_as_current_span(self, name):
    # 1. Check if there's a current span in context
    parent_span = context.get_current_span()
    
    # 2. Create new span with parent reference
    new_span = Span(name=name, parent=parent_span)
    
    # 3. Set new span as current in context
    context.set_current_span(new_span)
    
    # 4. Return span for use in 'with' block
    return new_span
```

---

### FastAPIInstrumentor (Reads Context)

**How FastAPIInstrumentor creates spans:**

```python
# Inside FastAPIInstrumentor (conceptual code)
async def instrumented_handler(request):
    tracer = trace.get_tracer("opentelemetry.instrumentation.fastapi")
    
    # Reads current span from context (finds trace_middleware span!)
    with tracer.start_as_current_span("GET /api/services/list") as span:
        # Because trace_middleware span is in context,
        # this becomes a CHILD span automatically
        
        response = await original_handler(request)
        return response
```

**Key insight:**
- FastAPIInstrumentor doesn't know about your custom middleware
- It just follows OpenTelemetry convention: read current span from context
- Because custom middleware set a span in context, nesting happens automatically

---

## When Each Layer Creates Spans

### Scenario 1: Both Instrumentation Layers Work

**Result:** Two nested spans (current behavior)

```
trace_middleware span [parent]
└── FastAPIInstrumentor span [child]
    └── Route handler [grandchild, if instrumented]
```

**Pros:**
- Guaranteed tracing even if one layer fails
- Can compare both implementations
- Full redundancy

**Cons:**
- Duplicate span names
- Slightly higher overhead (2x span creation)
- More data stored in telemetry backend

---

### Scenario 2: Only Custom Middleware Works

**Result:** Single span from custom middleware

```
trace_middleware span [root]
└── Route handler [child, if instrumented]
```

**When this happens:**
- FastAPIInstrumentor fails to initialize
- Tracer provider not set before instrumentation
- Configuration issues

**Impact:**
- Still have HTTP tracing (good!)
- Missing FastAPI-specific attributes (http.route, etc.)

---

### Scenario 3: Only FastAPIInstrumentor Works

**Result:** Single span from FastAPIInstrumentor

```
FastAPIInstrumentor span [root]
└── Route handler [child, if instrumented]
```

**When this happens:**
- Custom middleware is removed
- Custom middleware fails to create spans

**Impact:**
- Standard OpenTelemetry instrumentation
- No redundancy, but cleaner traces

---

## Technical Details: Context Variables

### How Python's contextvars Works

```python
from contextvars import ContextVar

# OpenTelemetry uses this internally
_CURRENT_SPAN = ContextVar("current_span", default=None)

# Custom middleware
def trace_middleware(request, call_next):
    span = Span("parent")
    
    # Store span in context
    token = _CURRENT_SPAN.set(span)
    
    try:
        # call_next() runs in same context
        response = call_next(request)
        return response
    finally:
        # Restore previous context
        _CURRENT_SPAN.reset(token)
```

**Key properties:**
- Thread-safe and async-safe (survives `await` calls)
- Automatically propagates through `await call_next()`
- Isolated per-request (no cross-request contamination)

---

### Why `call_next()` Preserves Context

```python
# Custom middleware
async def trace_middleware(request, call_next):
    with tracer.start_as_current_span("parent") as span:
        # Span stored in context
        
        # This await doesn't lose the context!
        response = await call_next(request)
        
        # Span still in context here
        return response
```

**Why context survives:**
1. `contextvars` is designed for async/await
2. Context is propagated through task switches
3. Each request has isolated context (no leakage)

---

## Comparison: What Each Layer Captures

### Custom Middleware Attributes

```json
{
  "span.name": "GET /api/services/list",
  "http.method": "GET",
  "http.url": "http://localhost:8000/api/services/list?time_range=1h",
  "http.status_code": 200
}
```

**Limitations:**
- Captures full URL path (not route pattern)
- No FastAPI-specific attributes
- No automatic exception recording

---

### FastAPIInstrumentor Attributes

```json
{
  "span.name": "GET /api/services/list",
  "http.method": "GET",
  "http.url": "http://localhost:8000/api/services/list?time_range=1h",
  "http.status_code": 200,
  "http.scheme": "http",
  "http.target": "/api/services/list?time_range=1h",
  "http.route": "/api/services/list",
  "http.server_name": "localhost",
  "net.host.port": 8000,
  "fastapi.route_path": "/api/services/list",
  "fastapi.route_name": "get_services"
}
```

**Advantages:**
- Captures route pattern (important for grouping)
- More semantic attributes
- Automatic exception recording
- Follows OpenTelemetry semantic conventions

---

## Production Decision: Which to Keep?

### Option A: Keep Only FastAPIInstrumentor (Recommended)

```python
# Remove custom middleware
# @app.middleware('http')
# async def trace_middleware(request: Request, call_next):
#     ...

# Keep automatic instrumentation
FastAPIInstrumentor.instrument_app(app)
```

**When to choose:**
- FastAPIInstrumentor reliably creates spans
- Want standard OpenTelemetry attributes
- Prefer less maintenance

**Result:**
- Single span per request
- Clean traces
- Standard attributes

---

### Option B: Keep Only Custom Middleware

```python
# Remove automatic instrumentation
# FastAPIInstrumentor.instrument_app(app)

# Keep custom middleware
@app.middleware('http')
async def trace_middleware(request: Request, call_next):
    # Enhanced with more attributes
    ...
```

**When to choose:**
- Need custom span naming (e.g., sanitize URLs)
- Want application-specific attributes
- FastAPIInstrumentor causes issues

**Result:**
- Full control over instrumentation
- Custom attributes
- More maintenance required

---

### Option C: Keep Both for Different Purposes

```python
# Custom middleware for custom attributes
@app.middleware('http')
async def trace_middleware(request: Request, call_next):
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("custom.http.request") as span:
        # Add custom attributes only
        span.set_attribute('user.authenticated', bool(request.headers.get('X-Token')))
        span.set_attribute('app.version', '1.0.0')
        
        # Don't duplicate HTTP attributes (FastAPIInstrumentor handles those)
        response = await call_next(request)
        return response

# FastAPIInstrumentor for standard HTTP attributes
FastAPIInstrumentor.instrument_app(app)
```

**When to choose:**
- Need both custom and standard attributes
- Want custom span naming while keeping automatic instrumentation
- Comfortable with nested spans

**Result:**
- Two spans per request (intentional)
- Custom span for application logic
- FastAPI span for HTTP semantics
- Clear separation of concerns

---

## Summary

**How they work together:**
1. Custom middleware creates **parent span** via `start_as_current_span()`
2. Span is stored in **thread-local context** via `contextvars`
3. `call_next()` invokes FastAPIInstrumentor (preserves context)
4. FastAPIInstrumentor reads context, finds parent span
5. FastAPIInstrumentor creates **child span** automatically
6. Both spans close when their respective scopes exit

**Key mechanism:** Python's `contextvars` + OpenTelemetry's context propagation

**Current state:** Dual instrumentation creates nested parent-child spans

**Recommendation:** Remove one layer once you verify the other works reliably
