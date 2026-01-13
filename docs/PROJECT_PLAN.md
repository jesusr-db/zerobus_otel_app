# Observability Dashboard - Project Plan & Roadmap

**Project**: Databricks Observability Dashboard with Lakebase Migration
**Current Branch**: `lakebasesync`
**Status**: 🟡 MVP Complete, Migration In Progress, Production Readiness Pending
**Last Updated**: 2026-01-05

---

## Executive Summary

Building a modern observability dashboard for Databricks Apps that:
- Visualizes service dependencies and health metrics
- Provides real-time monitoring with auto-refresh
- Migrates from SQL Warehouse to Lakebase (PostgreSQL) backend
- Features trace analysis with waterfall visualization
- **NEW**: AI-powered chatbot for natural language observability queries

---

## Current Project State

### ✅ Phase 1-2: Core Infrastructure Complete

**Backend**:
- ✅ FastAPI with SQL Warehouse integration
- ✅ Databricks SDK integration
- ✅ Pydantic models for observability data
- ✅ Auto-refresh with React Query (30s intervals)

**Frontend**:
- ✅ React with TypeScript and Vite
- ✅ Dark theme with shadcn/ui components
- ✅ Time range selector (15m, 1h, 24hr)
- ✅ Multiple view layouts

**Visualizations**:
- ✅ Service dependency graph (D3.js force-directed)
- ✅ Service health metrics display
- ✅ Dashboard view with health cards
- ✅ Service list view with sorting/filtering
- ✅ Basic trace viewing

**Lakebase Migration** (Validated):
- ✅ PostgreSQL connection manager with OAuth
- ✅ Native PostgreSQL query patterns validated
- ✅ Schema discovery and validation endpoints
- ✅ Permission setup automation (Job + Scripts)
- ✅ Feature flag system (`DATA_BACKEND` env var)
- ✅ SQL converter (Spark SQL → PostgreSQL) - partially working

### 🟡 In Progress

**Waterfall Visualization**:
- Frontend: `client/src/pages/TracingAnalysisView.tsx`
- Backend: `/api/traces/waterfall/{trace_id}`
- **Issue**: Implementation has bugs (commit: "working on waterfall viz - not working")

**Lakebase Integration**:
- Native queries work in validation endpoints
- Production routers need migration
- LAKEBASE_HOST configuration hardcoded

### ❌ Not Started

**Phase 3: Time-Based Investigation View and cleanup phase2** (PRD P0):
- METRICS view is only showing last events - and not aggregating based on timeframe
- fix dependency map panel
- ✅ add secret scope for OTEL_TOKEN (COMPLETED - see backlog for details)
- Three-panel unified timeline (Metrics + Traces + Logs)
- Interactive timeline with zoom/pan
- Cross-signal correlation features

**AI Chatbot Integration** (Enhancement):
- Foundation model integration (MAS)
- Knowledge Agent with RAG
- Genie SQL generation
- Chat UI interface

---

## Critical Path Tasks

### 🔴 CRITICAL BLOCKERS (Week 1)

#### 1. Fix Automatic LAKEBASE_HOST Detection
**Priority**: P0 🚨
**Duration**: 2 days
**Impact**: Deployment automation blocked

**Current Problem**:
```yaml
# app.yml:21-22 - Hardcoded host
LAKEBASE_HOST: instance-fc55fde4-a0a8-4e28-beca-73f5a4833f4e.database.cloud.databricks.com
```

**Solution**:
```python
# server/services/lakebase_manager.py
def _auto_detect_host(self):
    """Auto-discover Lakebase instance host"""
    instance = self.client.database_instances.get(self.instance_name)
    return instance.connection_details.host
```

**Files to Update**:
- `server/services/lakebase_manager.py:44`
- `app.yml:21-22` (remove hardcoded host)
- `resources/grant_permissions_job.yml:20`

**Testing**:
```bash
# Verify auto-detection works
uv run python -c "
from server.services.lakebase_manager import LakebaseManager
manager = LakebaseManager()
print(f'Auto-detected host: {manager.db_host}')
"
```

---

#### 2. Debug and Fix Waterfall Visualization
**Priority**: P0 🚨
**Duration**: 2 days
**Impact**: Core feature non-functional

**Investigation Steps**:
1. Test `/api/traces/waterfall/{trace_id}` endpoint
2. Validate span hierarchy building (`TracingAnalysisView.tsx:88`)
3. Test JSONB span extraction with Lakebase
4. Fix parent-child relationship logic

**Test Cases**:
```bash
# Test waterfall endpoint
curl http://localhost:8000/api/traces/waterfall/{trace_id} | jq

# Verify span_details structure
uv run python discover_lakebase_schema.py
```

**Code Locations**:
- Frontend: `client/src/pages/TracingAnalysisView.tsx`
- Backend: `server/routers/traces.py`
- Data model: JSONB `span_details` with `jsonb_array_elements`

---

#### 3. Complete Lakebase Router Migration
**Priority**: P1
**Duration**: 1 day
**Impact**: Feature flag not fully functional

**Routers to Migrate**:
- [x] `/api/services/list` - Partially done
- [ ] `/api/services/{service_name}/metrics`
- [ ] `/api/dependencies/graph`
- [x] `/api/traces` - Exists, needs Lakebase variant
- [ ] `/api/traces/waterfall/{trace_id}` - Needs JSONB extraction

**Migration Pattern**:
```python
# server/routers/services.py
from server.config import DATA_BACKEND
from server.services.lakebase_manager import LakebaseManager
from server.services.warehouse_manager import WarehouseManager

@router.get("/list")
async def get_services_list(time_range: str):
    if DATA_BACKEND == "lakebase":
        query = """
        WITH current_spans AS (
          SELECT
            span_value->>'service_name' as service_name,
            (span_value->>'duration_ms')::float as duration_ms,
            (span_value->>'is_error')::boolean as is_error
          FROM zerobus_sdp.traces_assembled_synced t
          CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
          WHERE t.trace_start >= NOW() - INTERVAL '{time_range}'
        )
        SELECT service_name, COUNT(*) as request_count, AVG(duration_ms) as avg_duration
        FROM current_spans
        GROUP BY service_name
        """
        return LakebaseManager().execute_query(query)
    else:
        return WarehouseManager().execute_query(spark_query)
```

---

### 🟡 HIGH PRIORITY (Week 2)

#### 4. Implement Time-Based Investigation View
**Priority**: P1 (PRD Phase 3 - P0 Feature)
**Duration**: 3 days
**Impact**: Critical missing feature for incident investigation

**PRD Requirement** (docs/product.md:79-108):
> "Unified time-series visualization for correlating metrics, traces, and logs"

**Components to Build**:

1. **TimelineView Container** (`client/src/pages/TimelineView.tsx`)
```typescript
interface TimelineViewProps {
  timeRange: TimeRange;
  services: string[];
}

export function TimelineView({ timeRange, services }: TimelineViewProps) {
  return (
    <div className="h-full flex flex-col">
      {/* Shared time axis controls */}
      <TimelineControls />

      {/* Three synchronized panels */}
      <div className="flex-1 grid grid-rows-3">
        <MetricsTimelinePanel />
        <TracesTimelinePanel />
        <LogsTimelinePanel />
      </div>
    </div>
  );
}
```

2. **Metrics Panel** - Time-series charts synchronized to timeline
3. **Traces Panel** - Waterfall list with timeline markers
4. **Logs Panel** - Log events with severity colors (if `logs_synced` available)

**Dependencies**:
- Waterfall visualization must work (Task #2)
- Lakebase metrics queries (Task #3)
- Logs table integration

**API Endpoints Needed**:
```python
# server/routers/timeline.py
@router.get("/metrics-timeseries")
async def get_metrics_timeseries(
    services: list[str],
    start_time: datetime,
    end_time: datetime,
    bucket_size: str = "1m"
)

@router.get("/traces-timeline")
async def get_traces_timeline(
    services: list[str],
    start_time: datetime,
    end_time: datetime
)

@router.get("/logs-timeline")
async def get_logs_timeline(
    services: list[str],
    start_time: datetime,
    end_time: datetime,
    severity: list[str] = ["ERROR", "WARN"]
)
```

---

#### 5. Lakebase Permissions Testing
**Priority**: P2
**Duration**: 1 day
**Impact**: May fail in production

**Testing Checklist**:
```bash
# 1. Deploy permission job
databricks bundle deploy --target dev

# 2. Run job to grant permissions
databricks jobs run-now --job-id <grant-permissions-job-id>

# 3. Validate permissions
uv run python discover_lakebase_schema.py

# 4. Test OAuth token refresh (wait 15 minutes)
uv run python -c "
from server.services.lakebase_manager import LakebaseManager
import time

manager = LakebaseManager()
result1 = manager.execute_query('SELECT 1')
print('First query successful')

time.sleep(900)  # Wait 15 minutes

result2 = manager.execute_query('SELECT 1')
print('Token refresh successful')
"
```

**Validation Requirements**:
- [ ] Service principal has `DATABRICKS_SUPERUSER` role
- [ ] Can connect to `zerobus_sdp` database
- [ ] Can query `traces_assembled_synced` table
- [ ] OAuth token refresh works (15-min intervals)

---

#### 6. Performance Testing & Optimization
**Priority**: P2
**Duration**: 1 day
**Impact**: Unknown production scalability

**Testing Matrix**:

| Metric | SQL Warehouse | Lakebase | Target | Status |
|--------|--------------|----------|--------|--------|
| Query latency (services list) | ? | < 1s | < 2s | ⏳ |
| Auto-refresh impact | ? | ? | No UI blocking | ⏳ |
| Large graph (100+ services) | ? | ? | < 3s load | ⏳ |
| Time range change | ? | ? | < 2s | ⏳ |
| Waterfall render (50 spans) | ? | ? | < 1s | ⏳ |

**Optimization Strategies**:
- Add query result caching (5-10s TTL)
- Implement pagination for large trace lists
- Use PostgreSQL prepared statements
- Add database connection pooling metrics
- Optimize D3.js rendering for large graphs

**Performance Profiling**:
```python
# server/middleware/performance.py
import time
from fastapi import Request

@app.middleware("http")
async def add_performance_headers(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Log slow queries
    if process_time > 2.0:
        logger.warning(f"Slow request: {request.url.path} took {process_time:.2f}s")

    return response
```

---

## Week 3-4: AI Chatbot Implementation 🤖

### Feature Overview

**AI-powered conversational interface** for observability data that enables:
- Natural language queries about service health, traces, and metrics
- Intelligent data retrieval using RAG (Retrieval Augmented Generation)
- SQL generation for custom observability queries via Genie
- Context-aware responses based on current system state

---

### Architecture Components

#### 1. Foundation Models (Model As a Service)

**Databricks Model Serving Integration**:

```python
# server/services/llm_client.py
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

class LLMClient:
    def __init__(self):
        self.client = WorkspaceClient()
        self.endpoint_name = "databricks-meta-llama-3-1-70b-instruct"

    async def query(self, prompt: str, system_prompt: str = None) -> str:
        """Query foundation model via Model Serving"""
        messages = []

        if system_prompt:
            messages.append(ChatMessage(
                role=ChatMessageRole.SYSTEM,
                content=system_prompt
            ))

        messages.append(ChatMessage(
            role=ChatMessageRole.USER,
            content=prompt
        ))

        response = self.client.serving_endpoints.query(
            name=self.endpoint_name,
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )

        return response.choices[0].message.content
```

**Recommended Models**:
- **Claude 3.5 Sonnet** (via Databricks MAS) - Best for analysis
- **Llama 3.1 70B Instruct** - Open-source alternative
- **GPT-4** - Via Azure OpenAI integration

---

#### 2. Knowledge Agents (RAG Integration)

**Retrieval-Augmented Generation for Observability Context**:

```python
# server/services/knowledge_base.py
from langchain.vectorstores import FAISS
from langchain.embeddings import DatabricksEmbeddings
from langchain.docstore.document import Document

class ObservabilityKnowledgeBase:
    """
    Manages embeddings and retrieval for observability context
    """

    def __init__(self):
        self.embeddings = DatabricksEmbeddings()
        self.documents = self._load_documents()
        self.vectorstore = self._create_vectorstore()

    def _load_documents(self) -> list[Document]:
        """Load runbooks, service docs, and incident histories"""
        return [
            # Service runbooks
            Document(
                page_content="""
                Frontend Service Runbook:
                - Typical failures occur when Redis is unavailable
                - High error rates usually indicate database connection issues
                - Latency spikes often caused by slow API responses from payment service
                - Critical dependencies: Redis, PostgreSQL, Payment API
                """,
                metadata={"type": "runbook", "service": "frontend"}
            ),

            # Alert definitions
            Document(
                page_content="""
                Critical Alert Thresholds:
                - Error rate > 5%: Critical service degradation
                - P95 latency > 1000ms: Performance degradation
                - Request rate drop > 50%: Potential service outage
                - Memory usage > 85%: Resource exhaustion risk
                """,
                metadata={"type": "alert", "severity": "critical"}
            ),

            # Historical incidents
            Document(
                page_content="""
                Major Incident: 2025-12-15
                - Root Cause: Database connection pool exhaustion
                - Services Affected: Frontend, API Gateway, Payment
                - Duration: 45 minutes
                - Resolution: Increased connection pool size from 20 to 50
                - Prevention: Added connection pool monitoring alerts
                """,
                metadata={"type": "incident", "date": "2025-12-15"}
            ),

            # Best practices
            Document(
                page_content="""
                Debugging High Error Rates:
                1. Check service logs for exception traces
                2. Verify database connectivity and query performance
                3. Review recent deployments (last 2 hours)
                4. Check dependent service health
                5. Validate cache layer (Redis) availability
                6. Review circuit breaker states
                """,
                metadata={"type": "best_practice", "category": "debugging"}
            )
        ]

    def _create_vectorstore(self) -> FAISS:
        """Create FAISS vector store from documents"""
        return FAISS.from_documents(
            documents=self.documents,
            embedding=self.embeddings
        )

    def search(self, query: str, k: int = 3) -> list[Document]:
        """Semantic search for relevant knowledge"""
        return self.vectorstore.similarity_search(query, k=k)

    def add_incident(self, incident_summary: str, metadata: dict):
        """Add new incident to knowledge base"""
        doc = Document(
            page_content=incident_summary,
            metadata={**metadata, "type": "incident"}
        )
        self.documents.append(doc)
        # Re-index vectorstore
        self.vectorstore = self._create_vectorstore()
```

**Knowledge Sources**:
- Service runbooks and documentation
- Historical incident patterns
- Alert definitions and thresholds
- Team escalation procedures
- Best practices and debugging guides

---

#### 3. Genie Integration (SQL Query Generation)

**Natural Language to SQL for Observability Queries**:

```python
# server/services/genie_client.py
from databricks.sdk import WorkspaceClient

class GenieQueryGenerator:
    """
    Converts natural language to SQL using Databricks Genie
    """

    def __init__(self):
        self.client = WorkspaceClient()
        self.space_id = self._get_or_create_space()

    def _get_or_create_space(self) -> str:
        """
        Get or create Genie space for observability queries

        Genie spaces provide context for SQL generation:
        - Tables: traces_assembled_synced, service_dependancy, etc.
        - Schema: zerobus_sdp
        - Descriptions: Service names, metric definitions
        """
        # Check if space exists
        spaces = self.client.genie.list_spaces()
        for space in spaces:
            if space.name == "observability-queries":
                return space.space_id

        # Create new space
        space = self.client.genie.create_space(
            name="observability-queries",
            description="Natural language queries for observability data",
            tables=[
                "zerobus_sdp.traces_assembled_synced",
                "zerobus_sdp.service_dependancy",
                "zerobus_sdp.metrics_1min_synced",
                "zerobus_sdp.logs_synced"
            ]
        )
        return space.space_id

    async def generate_sql(self, natural_language_query: str) -> dict:
        """
        Convert natural language to SQL using Genie

        Examples:
        - "Show me services with error rate > 5% in last hour"
        - "List traces longer than 1 second from frontend service"
        - "What services depend on the payment service?"
        """
        # Query Genie API
        response = self.client.genie.query(
            space_id=self.space_id,
            query=natural_language_query
        )

        return {
            "sql": response.sql_query,
            "explanation": response.explanation,
            "tables_used": response.tables,
            "confidence": response.confidence_score
        }

    async def execute_natural_query(self, question: str) -> dict:
        """Execute natural language query and return formatted results"""
        # Generate SQL
        genie_response = await self.generate_sql(question)

        # Execute against appropriate backend
        from server.config import DATA_BACKEND
        from server.services.lakebase_manager import LakebaseManager
        from server.services.warehouse_manager import WarehouseManager

        if DATA_BACKEND == "lakebase":
            # Convert Spark SQL to PostgreSQL if needed
            sql = self._convert_to_postgres(genie_response["sql"])
            results = LakebaseManager().execute_query(sql)
        else:
            results = WarehouseManager().execute_query(genie_response["sql"])

        return {
            "question": question,
            "sql_generated": genie_response["sql"],
            "explanation": genie_response["explanation"],
            "results": results,
            "row_count": len(results)
        }

    def _convert_to_postgres(self, spark_sql: str) -> str:
        """Convert Spark SQL to PostgreSQL syntax"""
        # Handle JSONB array operations
        sql = spark_sql.replace(
            "explode(span_details)",
            "jsonb_array_elements(span_details)"
        )
        # Handle field access
        sql = sql.replace("span_value.field", "span_value->>'field'")
        return sql
```

**Genie Use Cases**:
- Ad-hoc observability queries without SQL knowledge
- Complex analytical questions
- Historical trend analysis
- Root cause investigation queries

**Example Queries**:
```
User: "Show me services with error rate > 5% in last hour"
Genie SQL:
WITH service_errors AS (
  SELECT
    span_value->>'service_name' as service_name,
    COUNT(*) as total_requests,
    SUM(CASE WHEN (span_value->>'is_error')::boolean THEN 1 ELSE 0 END) as error_count
  FROM zerobus_sdp.traces_assembled_synced t
  CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
  WHERE t.trace_start >= NOW() - INTERVAL '1 hour'
  GROUP BY span_value->>'service_name'
)
SELECT
  service_name,
  error_count,
  total_requests,
  (error_count::float / total_requests * 100) as error_rate_pct
FROM service_errors
WHERE (error_count::float / total_requests) > 0.05
ORDER BY error_rate_pct DESC;
```

---

### Implementation Timeline

#### Phase 1: Foundation Model Integration (Days 1-3)

**Day 1: Backend Setup**
- Create `server/services/llm_client.py` - Foundation model client
- Create `server/routers/chatbot.py` - Chat API endpoints
- Add Pydantic models for chat requests/responses
- Test basic LLM queries

**Day 2: Query Classification**
```python
# server/services/query_classifier.py
class QueryClassifier:
    """Classify user queries into categories"""

    def classify(self, message: str) -> str:
        """
        Classify query type:
        - "diagnostic": "Why is X slow?", "What's causing errors?"
        - "data": "Show me...", "List all...", "What services..."
        - "general": "How do I...", "What does X mean?"
        """
        # Use LLM to classify
        prompt = f"""
        Classify this observability query:
        "{message}"

        Categories:
        - diagnostic: Questions about why something is wrong
        - data: Requests to show or list data
        - general: General questions or help

        Return only the category name.
        """
        category = llm_client.query(prompt)
        return category.strip().lower()
```

**Day 3: Basic Chat API**
```python
# server/routers/chatbot.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])

class ChatRequest(BaseModel):
    message: str
    context: dict = {}  # Current UI context

class ChatResponse(BaseModel):
    response: str
    sql_query: str | None = None
    data: dict | None = None
    sources: list[str] = []
    suggested_actions: list[dict] = []

@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Handle conversational queries about observability data
    """
    classifier = QueryClassifier()
    query_type = classifier.classify(request.message)

    if query_type == "data":
        return await handle_genie_query(request)
    elif query_type == "diagnostic":
        return await handle_diagnostic_query(request)
    else:
        return await handle_general_chat(request)

async def handle_general_chat(request: ChatRequest) -> ChatResponse:
    """Handle general questions"""
    system_prompt = """
    You are an observability expert assistant for a Databricks-based system.
    Help users understand their observability data and troubleshoot issues.
    Be concise and actionable.
    """

    response = await llm_client.query(
        prompt=request.message,
        system_prompt=system_prompt
    )

    return ChatResponse(
        response=response,
        sources=["llm"]
    )
```

**Testing**:
```bash
# Test LLM integration
curl -X POST http://localhost:8000/api/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is observability?",
    "context": {}
  }'
```

---

#### Phase 2: Knowledge Agent with RAG (Days 4-6)

**Day 4: Knowledge Base Setup**
- Create `server/services/knowledge_base.py`
- Load service runbooks and documentation
- Create FAISS vector store
- Test semantic search

**Day 5: Diagnostic Query Handler**
```python
# server/routers/chatbot.py (continued)
async def handle_diagnostic_query(request: ChatRequest) -> ChatResponse:
    """
    Handle diagnostic questions like:
    - "Why is service X slow?"
    - "What's causing errors in service Y?"
    - "Should I be concerned about this latency spike?"
    """

    # Get current service metrics if context provided
    service_data = {}
    if "service_name" in request.context:
        service_data = await get_service_metrics(
            request.context["service_name"],
            request.context.get("time_range", "1h")
        )

    # Retrieve relevant knowledge
    kb = ObservabilityKnowledgeBase()
    relevant_docs = kb.search(request.message, k=3)

    # Build context-aware prompt
    context_info = ""
    if service_data:
        context_info = f"""
Current Service Metrics:
- Service: {service_data.get('service_name')}
- Health Status: {service_data.get('health_status')}
- Error Rate: {service_data.get('error_rate', 0):.2f}%
- P95 Latency: {service_data.get('latency_p95', 0):.2f}ms
- Request Count: {service_data.get('request_count', 0)}
"""

    knowledge_context = "\n\n".join([
        f"Knowledge ({doc.metadata.get('type')}): {doc.page_content}"
        for doc in relevant_docs
    ])

    system_prompt = """
You are an expert observability engineer analyzing service health.
Provide concise diagnostic answers with:
1. Root cause assessment
2. Severity evaluation (Low/Medium/High/Critical)
3. Recommended actions (numbered list)
4. Related services to check

Be specific and actionable.
"""

    prompt = f"""
{context_info}

Relevant Context:
{knowledge_context}

User Question: {request.message}

Provide a diagnostic assessment.
"""

    response = await llm_client.query(
        prompt=prompt,
        system_prompt=system_prompt
    )

    # Extract suggested actions from response
    suggested_actions = _extract_actions(response)

    return ChatResponse(
        response=response,
        data=service_data,
        sources=[doc.metadata.get("type") for doc in relevant_docs],
        suggested_actions=suggested_actions
    )

def _extract_actions(response: str) -> list[dict]:
    """Extract actionable items from LLM response"""
    actions = []
    lines = response.split('\n')

    for line in lines:
        # Look for numbered actions
        if line.strip().startswith(('1.', '2.', '3.', '4.', '5.')):
            action_text = line.strip()[2:].strip()
            actions.append({
                "action": action_text,
                "type": "manual"  # or "automated" if we can execute it
            })

    return actions
```

**Day 6: Context Management**
```python
# server/services/context_manager.py
class ConversationContext:
    """Manage conversation history and context"""

    def __init__(self):
        self.conversations = {}  # user_id -> messages

    def add_message(self, user_id: str, role: str, content: str):
        """Add message to conversation history"""
        if user_id not in self.conversations:
            self.conversations[user_id] = []

        self.conversations[user_id].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })

        # Keep last 10 messages only
        self.conversations[user_id] = self.conversations[user_id][-10:]

    def get_context(self, user_id: str) -> str:
        """Get conversation history as context string"""
        if user_id not in self.conversations:
            return ""

        messages = self.conversations[user_id]
        context_lines = []

        for msg in messages[-5:]:  # Last 5 messages
            context_lines.append(f"{msg['role']}: {msg['content']}")

        return "\n".join(context_lines)
```

**Testing**:
```bash
# Test diagnostic query with context
curl -X POST http://localhost:8000/api/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Why is the frontend service showing high error rate?",
    "context": {
      "service_name": "frontend",
      "time_range": "1h",
      "current_view": "service_detail"
    }
  }'
```

---

#### Phase 3: Genie SQL Generation (Days 7-8)

**Day 7: Genie Integration**
```python
# server/routers/chatbot.py (continued)
async def handle_genie_query(request: ChatRequest) -> ChatResponse:
    """
    Handle data queries like:
    - "Show services with error rate > 5%"
    - "List traces longer than 1 second"
    - "What services depend on the payment service?"
    """

    genie = GenieQueryGenerator()

    try:
        # Generate SQL from natural language
        result = await genie.execute_natural_query(request.message)

        # Format results for UI
        formatted_data = {
            "results": result["results"],
            "row_count": result["row_count"],
            "columns": list(result["results"][0].keys()) if result["results"] else []
        }

        return ChatResponse(
            response=result["explanation"],
            sql_query=result["sql_generated"],
            data=formatted_data,
            sources=["genie"],
            suggested_actions=[
                {
                    "action": "View results in table",
                    "type": "automated",
                    "handler": "show_data_table"
                },
                {
                    "action": "Export to CSV",
                    "type": "automated",
                    "handler": "export_csv"
                }
            ]
        )

    except Exception as e:
        logger.error(f"Genie query failed: {e}")
        return ChatResponse(
            response=f"I couldn't generate a query for that. Error: {str(e)}",
            sources=["error"]
        )
```

**Day 8: Query Refinement**
```python
# Handle query refinement and follow-ups
@router.post("/chat/refine")
async def refine_query(
    original_query: str,
    refinement: str,
    previous_sql: str
) -> ChatResponse:
    """
    Refine previous query based on user feedback

    Example:
    User: "Show services with errors"
    Bot: [Shows results]
    User: "Only show last 15 minutes"
    Bot: [Refines query with time filter]
    """

    prompt = f"""
Refine this SQL query based on user feedback:

Original Query: {original_query}
Generated SQL: {previous_sql}
User Refinement: {refinement}

Generate the refined SQL query.
"""

    refined_sql = await llm_client.query(prompt)

    # Execute refined query
    # ... (similar to handle_genie_query)
```

**Testing**:
```bash
# Test Genie data query
curl -X POST http://localhost:8000/api/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me the top 5 services by request count in the last hour",
    "context": {
      "time_range": "1h"
    }
  }'
```

---

#### Phase 4: Frontend Chat Interface (Days 9-10)

**Day 9: Chat UI Components**
```typescript
// client/src/components/ChatInterface.tsx
import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageSquare, Send, Sparkles, Database, AlertCircle } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sqlQuery?: string;
  data?: any;
  sources?: string[];
  suggestedActions?: Array<{
    action: string;
    type: string;
    handler?: string;
  }>;
  timestamp: number;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hi! I'm your observability assistant. I can help you:\n- Diagnose service issues\n- Query metrics and traces\n- Analyze error patterns\n\nWhat would you like to know?",
      timestamp: Date.now()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chatbot/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          message: input,
          context: {
            current_view: window.location.pathname,
            time_range: '1h',  // Get from context
            // Add more context as needed
          }
        })
      });

      if (!response.ok) {
        throw new Error('Chat request failed');
      }

      const data = await response.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response,
        sqlQuery: data.sql_query,
        data: data.data,
        sources: data.sources,
        suggestedActions: data.suggested_actions,
        timestamp: Date.now()
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (error) {
      console.error('Chat error:', error);

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: Date.now()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="border-b pb-4">
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-500" />
          Observability Assistant
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0">
        {/* Messages */}
        <ScrollArea ref={scrollRef} className="flex-1 p-4">
          <div className="space-y-4">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isLoading && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                <span>Thinking...</span>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input */}
        <div className="border-t p-4">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about services, traces, or metrics..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              size="icon"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>

          {/* Example queries */}
          <div className="mt-3 flex flex-wrap gap-2">
            <ExampleQuery
              query="Why is frontend slow?"
              onClick={setInput}
              icon={<AlertCircle className="w-3 h-3" />}
            />
            <ExampleQuery
              query="Show services with errors"
              onClick={setInput}
              icon={<Database className="w-3 h-3" />}
            />
            <ExampleQuery
              query="What caused the latency spike?"
              onClick={setInput}
              icon={<AlertCircle className="w-3 h-3" />}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] ${isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'} rounded-lg p-3`}>
        {/* Message content */}
        <p className="whitespace-pre-wrap">{message.content}</p>

        {/* SQL Query display */}
        {message.sqlQuery && (
          <div className="mt-2 p-2 bg-black/20 rounded text-xs font-mono">
            <div className="flex items-center gap-1 mb-1">
              <Database className="w-3 h-3" />
              <span className="font-semibold">Generated SQL:</span>
            </div>
            <code className="whitespace-pre-wrap">{message.sqlQuery}</code>
          </div>
        )}

        {/* Data table */}
        {message.data && message.data.results && (
          <div className="mt-2">
            <DataTable data={message.data.results} />
          </div>
        )}

        {/* Suggested actions */}
        {message.suggestedActions && message.suggestedActions.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {message.suggestedActions.map((action, idx) => (
              <Button
                key={idx}
                variant="outline"
                size="sm"
                className="text-xs"
                onClick={() => handleAction(action)}
              >
                {action.action}
              </Button>
            ))}
          </div>
        )}

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 text-xs opacity-70">
            Sources: {message.sources.join(', ')}
          </div>
        )}
      </div>
    </div>
  );
}

function ExampleQuery({
  query,
  onClick,
  icon
}: {
  query: string;
  onClick: (query: string) => void;
  icon?: React.ReactNode;
}) {
  return (
    <button
      onClick={() => onClick(query)}
      className="flex items-center gap-1 px-2 py-1 text-xs bg-muted hover:bg-muted/80 rounded-md transition-colors"
    >
      {icon}
      {query}
    </button>
  );
}

function DataTable({ data }: { data: any[] }) {
  if (!data || data.length === 0) return null;

  const columns = Object.keys(data[0]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b">
            {columns.map(col => (
              <th key={col} className="px-2 py-1 text-left font-semibold">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 5).map((row, idx) => (
            <tr key={idx} className="border-b">
              {columns.map(col => (
                <td key={col} className="px-2 py-1">
                  {JSON.stringify(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > 5 && (
        <p className="text-xs text-muted-foreground mt-1">
          Showing 5 of {data.length} results
        </p>
      )}
    </div>
  );
}

function handleAction(action: any) {
  // Handle suggested actions
  switch (action.handler) {
    case 'show_data_table':
      // Navigate to data view
      break;
    case 'export_csv':
      // Trigger CSV export
      break;
    default:
      console.log('Action:', action.action);
  }
}
```

**Day 10: Chat Integration & Positioning**
```typescript
// client/src/App.tsx
import { useState } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { Button } from './components/ui/button';
import { MessageSquare, X } from 'lucide-react';

export function App() {
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <div className="relative h-screen">
      {/* Main app content */}
      <MainLayout />

      {/* Floating chat button */}
      {!isChatOpen && (
        <Button
          className="fixed bottom-6 right-6 rounded-full w-14 h-14 shadow-lg"
          onClick={() => setIsChatOpen(true)}
        >
          <MessageSquare className="w-6 h-6" />
        </Button>
      )}

      {/* Chat panel */}
      {isChatOpen && (
        <div className="fixed bottom-6 right-6 w-96 h-[600px] shadow-2xl rounded-lg overflow-hidden z-50">
          <div className="relative h-full">
            <Button
              variant="ghost"
              size="icon"
              className="absolute top-2 right-2 z-10"
              onClick={() => setIsChatOpen(false)}
            >
              <X className="w-4 h-4" />
            </Button>
            <ChatInterface />
          </div>
        </div>
      )}
    </div>
  );
}
```

---

### Example Conversations

#### 1. Diagnostic Query
```
User: "Why is the frontend service showing 10% error rate?"
Assistant (with RAG context):
"I've analyzed the frontend service metrics and found:

**Root Cause Assessment:**
The 10% error rate is significantly above the 5% critical threshold. Based on historical patterns, this is likely caused by:
1. Database connection issues (most common cause for frontend errors)
2. Redis unavailability affecting session management
3. Downstream payment service timeout

**Current Metrics:**
- Error Rate: 10.2% (Critical - above 5% threshold)
- P95 Latency: 850ms (Elevated)
- Request Count: 1,245 requests in last hour
- Health Status: Critical

**Severity:** HIGH - Immediate attention required

**Recommended Actions:**
1. Check Redis connectivity: `redis-cli ping`
2. Review database connection pool usage
3. Verify payment service health status
4. Check recent deployments (last 2 hours)
5. Review error logs for exception traces

**Related Services:**
- Payment service (dependency)
- Redis cache layer
- PostgreSQL database

Would you like me to show you the error traces or check the payment service health?"
```

#### 2. Data Query (Genie)
```
User: "Show me all services with P95 latency > 500ms in the last hour"

Assistant (with Genie):
"Here are the services with high latency:

**SQL Query Generated:**
```sql
WITH service_latency AS (
  SELECT
    span_value->>'service_name' as service_name,
    PERCENTILE_CONT(0.95) WITHIN GROUP (
      ORDER BY (span_value->>'duration_ms')::float
    ) as p95_latency
  FROM zerobus_sdp.traces_assembled_synced t
  CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
  WHERE t.trace_start >= NOW() - INTERVAL '1 hour'
  GROUP BY span_value->>'service_name'
)
SELECT service_name, ROUND(p95_latency::numeric, 2) as p95_latency_ms
FROM service_latency
WHERE p95_latency > 500
ORDER BY p95_latency DESC;
```

**Results:**
| Service | P95 Latency (ms) |
|---------|------------------|
| payment | 1,245.67 |
| frontend | 850.23 |
| inventory | 678.45 |
| checkout | 542.12 |

Found 4 services with P95 latency exceeding 500ms. The payment service is showing the highest latency.

[View in table] [Export to CSV]"
```

#### 3. Follow-up Query
```
User: "What's causing the high latency in the payment service?"

Assistant (context-aware):
"Analyzing payment service latency...

**Analysis:**
Based on current metrics and historical patterns:

1. **Database Query Slowness**: Payment service queries are taking 800ms on average (normal: 50ms)
   - Likely cause: Missing index or table lock
   - Check: Recent schema changes or data volume growth

2. **External API Timeout**: Payment gateway API calls timing out
   - 15% of requests exceeding 3-second timeout
   - Check: Payment gateway status page

3. **Resource Contention**: High CPU usage (85%)
   - Container may be under-provisioned
   - Check: Memory and CPU limits

**Immediate Actions:**
1. Review slow query logs on payment database
2. Check payment gateway service status
3. Investigate recent payment service deployments
4. Consider scaling payment service pods

Would you like me to show traces for failed payment transactions?"
```

---

### Dependencies & Configuration

#### Backend Dependencies
```toml
# Add to pyproject.toml
[dependencies]
langchain = "^0.1.0"
langchain-community = "^0.0.10"
faiss-cpu = "^1.7.4"  # Vector similarity search
tiktoken = "^0.5.2"  # Token counting for LLMs
```

#### Environment Variables
```yaml
# app.yml
env:
  # Existing vars...

  # Chatbot configuration
  - name: CHATBOT_ENABLED
    value: "true"
  - name: LLM_ENDPOINT_NAME
    value: "databricks-meta-llama-3-1-70b-instruct"
  - name: GENIE_SPACE_ID
    value: "observability-queries"
  - name: CHATBOT_KNOWLEDGE_BASE_PATH
    value: "/dbfs/observability/knowledge_base"
```

#### Model Serving Permissions
```yaml
# app.yml
resources:
  # Existing resources...

  - name: llm-endpoint
    serving_endpoint:
      name: databricks-meta-llama-3-1-70b-instruct
      permission: CAN_QUERY

  - name: genie-space
    genie_space:
      id: observability-queries
      permission: CAN_QUERY
```

---

### Testing Strategy

#### Unit Tests
```python
# tests/test_chatbot.py
import pytest
from server.services.llm_client import LLMClient
from server.services.knowledge_base import ObservabilityKnowledgeBase
from server.services.genie_client import GenieQueryGenerator

def test_llm_client():
    """Test LLM client basic functionality"""
    client = LLMClient()
    response = await client.query("What is observability?")
    assert len(response) > 0
    assert "observability" in response.lower()

def test_knowledge_base_search():
    """Test knowledge base semantic search"""
    kb = ObservabilityKnowledgeBase()
    results = kb.search("high error rate troubleshooting")
    assert len(results) > 0
    assert any("error" in doc.page_content.lower() for doc in results)

def test_genie_sql_generation():
    """Test Genie SQL generation"""
    genie = GenieQueryGenerator()
    result = await genie.generate_sql("Show services with errors")
    assert "sql" in result
    assert "SELECT" in result["sql"].upper()
```

#### Integration Tests
```bash
# Test complete chat flow
curl -X POST http://localhost:8000/api/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me services with high error rates",
    "context": {"time_range": "1h"}
  }' | jq

# Test diagnostic query
curl -X POST http://localhost:8000/api/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Why is frontend slow?",
    "context": {
      "service_name": "frontend",
      "time_range": "1h"
    }
  }' | jq
```

---

### Performance Considerations

**LLM Response Time:**
- Target: < 2 seconds for simple queries
- Target: < 5 seconds for complex diagnostic queries
- Strategy: Use streaming responses for long outputs

**Knowledge Base Search:**
- Target: < 100ms for semantic search
- Strategy: Use FAISS GPU version for large knowledge bases
- Cache: LRU cache for frequent queries

**Genie SQL Generation:**
- Target: < 3 seconds including query execution
- Strategy: Cache common query patterns
- Fallback: If Genie unavailable, use template-based SQL generation

---

### Success Metrics

**Adoption:**
- [ ] 50% of active users try chatbot in first week
- [ ] Average 5+ queries per user session
- [ ] 80% positive feedback on responses

**Performance:**
- [ ] Response time < 2s for 95% of queries
- [ ] 90% query success rate (no errors)
- [ ] < 5% user query reformulations

**Quality:**
- [ ] 85% diagnostic accuracy (validated against known issues)
- [ ] 90% SQL query correctness
- [ ] < 10% hallucination rate

---

### Future Enhancements

**Post-MVP (Phase 2)**:
1. **Proactive Alerts**: Chatbot notifies users of detected anomalies
2. **Multi-turn Conversations**: Remember context across multiple exchanges
3. **Voice Interface**: Voice input for hands-free troubleshooting
4. **Automated Remediation**: Execute common fixes (restart service, scale up, etc.)
5. **Learning from Feedback**: Improve responses based on user thumbs up/down
6. **Custom Runbooks**: Users can add their own troubleshooting guides
7. **Collaborative Debugging**: Share chat sessions with team members
8. **Integration with Incident Management**: Create Jira tickets, PagerDuty alerts

---

## Summary Roadmap Timeline

### Week 1: Critical Blockers (Days 1-5)
- **Days 1-2**: Fix LAKEBASE_HOST auto-detection
- **Days 3-4**: Debug waterfall visualization
- **Day 5**: Complete Lakebase router migration

### Week 2: Core Features (Days 6-10)
- **Days 6-8**: Implement time-based investigation view
- **Days 9-10**: Testing, performance optimization, permissions validation

### Week 3-4: AI Chatbot (Days 11-20)
- **Days 11-13**: Foundation model integration (MAS)
- **Days 14-16**: Knowledge Agent with RAG
- **Days 17-18**: Genie SQL generation
- **Days 19-20**: Frontend chat interface

### Week 5: Production Deployment (Days 21-25)
- **Day 21**: Final integration testing
- **Day 22**: Performance benchmarking
- **Day 23**: Security review and deployment
- **Days 24-25**: Monitoring and bug fixes

---

## Deployment Checklist

### Pre-Deployment
- [ ] Fix LAKEBASE_HOST auto-detection
- [ ] Waterfall visualization working
- [ ] All routers support Lakebase backend
- [ ] Time-based investigation view complete
- [ ] Chatbot endpoints tested
- [ ] Permissions job validated
- [ ] Performance testing complete

### Deployment Steps
1. Run permission grant job
2. Deploy app with `DATA_BACKEND=lakebase` and `CHATBOT_ENABLED=true`
3. Monitor logs: `uv run python dba_logz.py <app-url> --duration 60`
4. Verify uvicorn startup messages
5. Test core endpoints with `dba_client.py`
6. Test chatbot with sample queries
7. Validate metrics in UI

### Post-Deployment Monitoring
- [ ] Check for Python exceptions in logs
- [ ] Validate OAuth token refresh (no 401 errors)
- [ ] Monitor query performance (Lakebase and Warehouse)
- [ ] Track LLM API usage and costs
- [ ] Monitor chatbot response quality
- [ ] User acceptance testing

---

## Risk Assessment

### High Risk 🔴
1. **LAKEBASE_HOST hardcoded** - Blocks deployment automation
2. **Waterfall bugs** - Core feature broken
3. **Missing investigation view** - Critical PRD requirement
4. **LLM costs** - Chatbot usage may be expensive

### Medium Risk 🟡
5. **Incomplete router migration** - Dual-maintenance burden
6. **Untested permissions** - May fail in production
7. **No performance baseline** - Unknown scalability
8. **Genie API availability** - Dependency on external service

### Low Risk 🟢
9. **SQL converter complexity** - Native queries are better
10. **Data freshness** - Lakebase sync lag acceptable
11. **Knowledge base coverage** - Can expand over time

---

## Open Questions

1. **Waterfall Issue**: What specifically is broken? Error messages? UI not rendering?
2. **Timeline Priority**: Is Phase 3 (Investigation View) required for initial release?
3. **Logs Integration**: Is `zerobus_sdp.logs_synced` table available and populated?
4. **Performance SLAs**: What are acceptable query latency targets?
5. **Deployment Target**: When is production release planned?
6. **LLM Budget**: What's the budget for foundation model API calls?
7. **Genie Access**: Do we have access to Genie API in production workspace?
8. **Chatbot Priority**: Should chatbot be in initial release or Phase 2?

---

## Files to Create/Update

### Critical Files
- `server/services/lakebase_manager.py:44` - LAKEBASE_HOST auto-detection
- `app.yml:21-22` - Remove hardcoded host
- `client/src/pages/TracingAnalysisView.tsx` - Fix waterfall bugs
- `server/routers/traces.py` - Waterfall Lakebase support

### New Files (Chatbot)
- `server/services/llm_client.py` - Foundation model client
- `server/services/knowledge_base.py` - RAG knowledge base
- `server/services/genie_client.py` - Genie SQL generation
- `server/services/query_classifier.py` - Query type classification
- `server/routers/chatbot.py` - Chat API endpoints
- `client/src/components/ChatInterface.tsx` - Chat UI
- `tests/test_chatbot.py` - Chatbot unit tests

### Updated Files
- `server/routers/services.py` - Complete Lakebase migration
- `server/routers/dependencies.py` - Add Lakebase support
- `client/src/pages/TimelineView.tsx` - Time-based investigation view
- `pyproject.toml` - Add chatbot dependencies
- `app.yml` - Add chatbot configuration

---

## Conclusion

This comprehensive project plan outlines:
- ✅ **Completed work**: MVP features and Lakebase validation
- 🟡 **Critical blockers**: LAKEBASE_HOST, waterfall bugs, router migration
- 🆕 **New feature**: AI chatbot with MAS, Knowledge Agents, and Genie
- 📅 **Timeline**: 5-week implementation plan
- ✅ **Success criteria**: Performance targets and metrics

**Next Steps**: Start with Week 1 critical blockers, then proceed with core features and AI chatbot implementation.

---

## Backlog: Issues & Technical Debt

### ✅ Issue #001: Databricks Secrets Configuration in Asset Bundles

**Date Resolved**: 2026-01-12
**Priority**: P0 (Deployment Blocker)
**Status**: RESOLVED

**Problem Summary**:
Deployment failed with error: "Error reading app.yml file, please ensure it is in the correct format" when attempting to reference Databricks secrets in a Databricks Asset Bundle configuration.

**Root Cause**:
Incorrect secrets reference format in app.yml. Used template syntax `value: {{secrets.otel-token}}` instead of proper Databricks Apps resource reference pattern.

**Incorrect Implementation**:

```yaml
# ❌ WRONG - app.yml (root)
env:
  - name: DATABRICKS_OTEL_TOKEN
    value: {{secrets.otel-token}}  # Incorrect template syntax

resources:
  - name: otel-token
    secret:
      scope: jmr_demo
      key: otel_token
      permission: READ
```

**Correct Implementation**:

```yaml
# ✅ CORRECT - app.yml (root)
env:
  - name: DATABRICKS_OTEL_TOKEN
    valueFrom: otel-token  # References resource name

# ✅ CORRECT - resources/app.yml (bundle configuration)
resources:
  apps:
    o11y_jmr_app:
      resources:
        - name: otel-token
          secret:
            scope: jmr_demo
            key: otel_token
            permission: READ
```

**Key Learnings**:

1. **Databricks Asset Bundles Architecture**:
   - Root `app.yml`: Contains runtime configuration (env vars, command)
   - `resources/app.yml`: Contains bundle resource definitions (secrets, warehouses, databases)
   - Both files work together during deployment

2. **Secret Reference Pattern**:
   - Use `valueFrom: <resource-name>` NOT `value: {{secrets.xxx}}`
   - The resource name must match between `resources/app.yml` and `app.yml`
   - Databricks injects secrets as environment variables at runtime

3. **Documentation Source**:
   - Official Databricks docs: <https://docs.databricks.com/aws/en/dev-tools/databricks-apps/secrets>
   - Retrieved via Context7 MCP for accurate, version-specific guidance

**Files Modified**:

- `app.yml:35-36` - Changed from `value:` to `valueFrom:`
- `resources/app.yml:8-12` - Added secret resource definition

**Verification Command**:

```bash
# Verify secret scope and key exist
databricks secrets list-scopes
databricks secrets list-secrets jmr_demo

# Deploy with corrected configuration
databricks bundle deploy --target dev
```

**Prevention**:

- Always use Context7 MCP to verify Databricks Apps configuration syntax
- Reference official documentation for resource configuration patterns
- Test bundle validation before deployment: `databricks bundle validate`

**Related Documentation**:

- Databricks Apps Secrets: <https://docs.databricks.com/aws/en/dev-tools/databricks-apps/secrets>
- Environment Variables: <https://docs.databricks.com/aws/en/dev-tools/databricks-apps/environment-variables>
- Bundle Resources: <https://docs.databricks.com/aws/en/dev-tools/bundles/resources>

---

### ⏳ Issue #002: Lakebase Host Auto-Detection

**Date Created**: 2026-01-12
**Priority**: P0 (Deployment Automation)
**Status**: BACKLOG - Not Started

**Problem Summary**:
The Lakebase database host is currently hardcoded in `app.yml`, which prevents deployment automation and requires manual updates when the database instance changes or is recreated.

**Current Hardcoded Configuration**:

```yaml
# app.yml:21-22 - HARDCODED HOST
- name: LAKEBASE_HOST
  value: instance-dc3ca2cf-029d-4fc3-a647-020486cc7d3e.database.cloud.databricks.com
```

**Impact**:

- Deployment fails when database instance is recreated (new host)
- Requires manual intervention to update `app.yml`
- Breaks CI/CD automation
- Risk of deploying with incorrect host configuration
- Cannot reliably switch between dev/staging/prod database instances

**Proposed Solution**:

Implement auto-detection of Lakebase host using Databricks SDK during application initialization:

```python
# server/services/lakebase_manager.py:44
def _auto_detect_host(self) -> str:
    """
    Auto-discover Lakebase instance host using Databricks SDK

    Returns:
        str: Database instance host (e.g., instance-xxx.database.cloud.databricks.com)

    Raises:
        ValueError: If instance not found or connection details unavailable
    """
    from databricks.sdk import WorkspaceClient

    client = WorkspaceClient()

    try:
        # Get instance details by name
        instance = client.database_instances.get(self.instance_name)

        # Extract host from connection details
        if instance.connection_details and instance.connection_details.host:
            host = instance.connection_details.host
            logger.info(f"Auto-detected Lakebase host: {host}")
            return host
        else:
            raise ValueError(f"No connection details found for instance: {self.instance_name}")

    except Exception as e:
        logger.error(f"Failed to auto-detect Lakebase host: {e}")
        raise ValueError(f"Could not auto-detect host for instance '{self.instance_name}': {e}")
```

**Implementation Plan**:

1. **Update LakebaseManager** (`server/services/lakebase_manager.py`):
   - Add `_auto_detect_host()` method
   - Call during `__init__` if `LAKEBASE_HOST` env var is not set
   - Add fallback to env var for local development override

2. **Remove Hardcoded Host** (`app.yml:21-22`):
   - Remove `LAKEBASE_HOST` environment variable entirely
   - Or change to optional override: `LAKEBASE_HOST: ""` (empty = auto-detect)

3. **Update Grant Permissions Job** (`resources/grant_permissions_job.yml:20`):
   - Remove hardcoded host reference
   - Use auto-detection in job script as well

4. **Add Validation Endpoint** (`server/routers/system.py`):
   - Add `/api/system/lakebase-info` endpoint
   - Return detected host, instance name, connection status
   - Useful for debugging deployment issues

**Testing Strategy**:

```bash
# Test auto-detection locally
uv run python -c "
from server.services.lakebase_manager import LakebaseManager
manager = LakebaseManager()
print(f'Detected host: {manager.db_host}')
print(f'Instance name: {manager.instance_name}')
"

# Test with explicit override
export LAKEBASE_HOST="custom-host.cloud.databricks.com"
uv run python -c "
from server.services.lakebase_manager import LakebaseManager
manager = LakebaseManager()
assert manager.db_host == 'custom-host.cloud.databricks.com', 'Override failed'
print('Override works correctly')
"

# Test deployment with auto-detection
databricks bundle deploy --target dev
# Check logs for "Auto-detected Lakebase host: ..."
uv run python dba_logz.py <app-url> --search "Auto-detected" --duration 30
```

**Files to Modify**:

- `server/services/lakebase_manager.py:44` - Add `_auto_detect_host()` method
- `server/services/lakebase_manager.py:__init__` - Call auto-detect if host not provided
- `app.yml:21-22` - Remove or make optional `LAKEBASE_HOST`
- `resources/grant_permissions_job.yml:20` - Remove hardcoded host
- `server/routers/system.py` - Add validation endpoint (optional)

**Dependencies**:

- `databricks.sdk` (already installed)
- `WorkspaceClient` must have permissions to read database instance metadata
- Service principal needs `CAN_USE` on database instance resource

**Risks & Mitigation**:

- **Risk**: Auto-detection fails during startup → App crashes
  - **Mitigation**: Add retry logic (3 attempts with exponential backoff)
  - **Mitigation**: Provide clear error messages for debugging
  - **Mitigation**: Support env var override for emergency fixes

- **Risk**: SDK API changes break auto-detection
  - **Mitigation**: Add comprehensive error handling
  - **Mitigation**: Log detailed error information
  - **Mitigation**: Support fallback to env var

- **Risk**: Performance impact from SDK call on every startup
  - **Mitigation**: Cache result in memory (single call per app lifetime)
  - **Mitigation**: SDK call is fast (<100ms typically)

**Success Criteria**:

- ✅ App starts successfully with auto-detected host
- ✅ No hardcoded hosts in configuration files
- ✅ Deployment succeeds without manual host updates
- ✅ Override via env var still works for edge cases
- ✅ Clear error messages if auto-detection fails
- ✅ Documented in deployment guide

**Related Issues**:

- See also: Task #1 in Critical Path (Week 1) - Same issue
- Blocks: CI/CD automation, multi-environment deployments
- Related: Issue #003 (future) - Auto-detect warehouse ID

**Priority Justification**:

P0 because:

- Blocks deployment automation (manual intervention required)
- High risk of production incidents (wrong host = app failure)
- Affects developer productivity (manual config updates)
- Required for proper multi-environment support (dev/staging/prod)
