# Observability Dashboard for Databricks (o11y-jmr)

A production-grade observability platform built entirely on Databricks, providing real-time service health monitoring, distributed tracing, log analysis, and dependency mapping for microservices architectures. Ingestion is powered by **ZeroBus OTEL** -- Databricks' native OpenTelemetry collector that lands traces, logs, and metrics directly into Unity Catalog Delta tables. Serving is powered by **Lakebase** -- Databricks' managed PostgreSQL -- delivering sub-second query latency to the dashboard via synced table reverse ETL from the Gold layer.

---

## Data Ingestion: ZeroBus OTEL

**ZeroBus OTEL** is the primary ingestion path for all observability signals in this application. It acts as a Databricks-native OpenTelemetry collector that receives standard OTLP data from instrumented services and writes it directly into Unity Catalog Delta tables.

```
Instrumented Services (OTLP)
        |
        v
 ┌──────────────────────┐
 │   ZeroBus OTEL       │   Databricks-native OTel collector
 │   Collector           │   Receives traces, logs, metrics via OTLP
 └──────┬───────────────┘
        │  Writes to Delta tables
        v
 ┌──────────────────────┐
 │  Bronze Layer         │   Raw OTel data in Unity Catalog
 │  otel_traces          │   (catalog.schema.otel_*)
 │  otel_logs            │
 │  otel_metrics         │
 └──────────────────────┘
        │
        v  DLT pipelines transform into Silver & Gold
```

**Why ZeroBus OTEL matters:**
- **Zero infrastructure** -- No self-hosted Jaeger, Prometheus, or ELK stack to manage
- **Native Delta format** -- OTel data lands directly in governed Unity Catalog tables, ready for SQL, DLT, and ML
- **Three signals, one path** -- Traces, logs, and metrics flow through a single collector into a unified lakehouse
- **Governed by default** -- All data inherits Unity Catalog access controls, lineage, and audit logging

The bronze tables produced by ZeroBus OTEL (`otel_traces`, `otel_logs`, `otel_metrics`) serve as the source for the Silver and Gold DLT pipelines that power this dashboard.

---

## Serving Layer: Lakebase (Managed PostgreSQL)

**Lakebase** is the low-latency serving backend that makes this dashboard fast. Rather than querying Delta tables through a SQL warehouse for every page load, the app reads from Lakebase -- Databricks' managed PostgreSQL service -- which holds synced replicas of the Gold-layer tables via reverse ETL.

```
 Gold Delta Tables (Unity Catalog)
        │
        │  Synced Tables (Reverse ETL)
        │  Continuous replication
        v
 ┌──────────────────────────────────────────────────┐
 │              Lakebase (PostgreSQL)                │
 │                                                   │
 │  traces_silver_synced     metrics_1min_synced     │
 │  logs_synced              service_dependencies_   │
 │  traces_assembled_synced    synced                │
 │                                                   │
 │  OAuth token refresh every 15 min                 │
 │  SQLAlchemy pool: 5 base / 10 max overflow        │
 │  SSL required                                     │
 └──────────────────────┬───────────────────────────┘
                        │  Sub-second queries
                        v
              FastAPI backend (server/)
```

**Why Lakebase as the serving layer:**
- **Sub-second query latency** -- PostgreSQL point lookups and indexed scans are orders of magnitude faster than warehouse-based queries for interactive dashboards
- **No warehouse compute cost** -- Dashboard queries hit Lakebase, not a SQL warehouse, eliminating per-query DBU costs for real-time polling
- **Always-on, no cold start** -- Unlike serverless warehouses, Lakebase is continuously available with no startup delay
- **Automatic sync** -- Synced tables replicate Gold-layer changes from Delta to PostgreSQL without custom ETL code
- **OAuth-native auth** -- The app authenticates to Lakebase using Databricks OAuth tokens (auto-refreshed every 15 minutes), no static credentials
- **Connection pooling** -- SQLAlchemy engine with pool pre-ping, connection recycling, and overflow handling for production reliability

**How it works at runtime:**
1. The FastAPI backend initializes a `LakebaseManager` on startup
2. Lakebase host is auto-discovered from the instance name via the Databricks SDK (or via `PGHOST` resource binding)
3. OAuth tokens are generated via `database.generate_database_credential()` and injected into every connection via SQLAlchemy's `do_connect` event
4. All dashboard API endpoints query Lakebase directly, returning results in milliseconds
5. The frontend polls these endpoints every 30 seconds for live updates

---

## Problems Addressed

| Problem | How This App Solves It |
|---------|----------------------|
| **Scattered observability data** | Unifies traces, logs, and metrics from raw OpenTelemetry data into a single interactive dashboard |
| **Slow incident investigation** | Shared timeline correlates metrics, traces, and logs so operators find root cause in clicks, not hours |
| **Service dependency blindness** | Interactive force-directed graph visualizes call relationships with live health overlays |
| **Performance debugging friction** | Trend charts with P50/P95/P99 latency breakdowns and historical baselines surface regressions instantly |
| **Error root-cause across boundaries** | Distributed trace waterfall shows exactly which span failed and in which service |
| **Dashboard query latency and cost** | Lakebase synced tables serve all dashboard queries at sub-second latency with zero warehouse compute cost |
| **No proactive monitoring** | 30-second auto-refresh with anomaly detection baselines keeps operators ahead of incidents |

---

## Target Personas

### Primary

- **Operations / SRE Teams** -- Monitor service health on always-on dashboards, drill into degraded services during incidents, correlate signals across metrics, logs, and traces.
- **Platform Engineers** -- Analyze service dependency topology, inspect span-level timing in distributed traces, debug inter-service latency and error propagation.

### Secondary

- **Engineering Managers / Business Stakeholders** -- Periodic check-ins on system health KPIs, request volume trends, and service availability summaries.

---

## Architecture

```
 Users (Browser + Databricks OAuth)
              |
              v
 ┌────────────────────────────────────────────────────────────┐
 │                   Databricks App (o11y-jmr)                │
 │                                                            │
 │  ┌──────────────────────┐   ┌───────────────────────────┐  │
 │  │  React / TypeScript  │   │  FastAPI (Python)         │  │
 │  │  Vite + shadcn/ui    │──>│  + OpenTelemetry auto-    │  │
 │  │  D3.js + Recharts    │   │    instrumentation        │  │
 │  │  React Query         │   │  Routers: services,       │  │
 │  └──────────────────────┘   │   deps, logs, traces,     │  │
 │         Port 5173           │   metrics                  │  │
 │                             └─────────┬─────────────────┘  │
 │                                       │ Port 8000          │
 └───────────────────────────────────────┼────────────────────┘
                                         │
                                         │ Primary query path
                                         v
                               ┌─────────────────────┐
                               │  ★ Lakebase ★        │
                               │  (Managed PostgreSQL) │
                               │  Sub-second queries   │
                               │  OAuth token refresh   │
                               │  Synced table replicas │
                               └──────────┬────────────┘
                                          │ Reverse ETL (synced tables)
                      ┌───────────────────┼───────────────────┐
                      v                                       v
            ┌──────────────────┐                    ┌──────────────────┐
            │  Unity Catalog   │                    │  SQL Warehouse   │
            │  Delta Tables    │                    │  (Serverless)    │
            │  Bronze / Silver │                    │  Dev / ad-hoc    │
            │  / Gold layers   │                    │  queries only    │
            └──────────────────┘                    └──────────────────┘

 ┌────────────────────────────────────────────────────────────┐
 │           Data Ingestion & Pipeline (DLT + Jobs)           │
 │                                                            │
 │  Instrumented       ZeroBus OTEL         Bronze Layer      │
 │  Services ──OTLP──> Collector ──Delta──> otel_traces       │
 │                                          otel_logs         │
 │                                          otel_metrics      │
 │                                                            │
 │  Bronze (ZeroBus) ──> Silver (DLT streaming)               │
 │    - flatten traces      - assemble traces                 │
 │    - enrich logs         - compute service health           │
 │    - flatten metrics                                       │
 │                                                            │
 │  Silver ──> Gold (DLT batch)                               │
 │    - service dependencies   - 1-min metric rollups         │
 │    - health summaries       - anomaly baselines            │
 │                                                            │
 │  Gold ──> Lakebase (Synced Tables / Reverse ETL)           │
 └────────────────────────────────────────────────────────────┘
```

---

## Databricks Services Used

| Service | Role |
|---------|------|
| **ZeroBus OTEL** | Native OpenTelemetry collector that ingests traces, logs, and metrics into Unity Catalog Delta tables (bronze layer) |
| **Databricks Apps** | Hosts the full-stack web application with OAuth authentication |
| **Lakebase (Managed PostgreSQL)** | Low-latency query backend via synced tables with OAuth token refresh |
| **Delta Live Tables (DLT)** | Silver streaming + Gold batch pipelines for data transformation |
| **Unity Catalog** | Governance, table lineage, and access control for all observability data |
| **SQL Warehouse (Serverless)** | Ad-hoc queries and development-mode data access |
| **Databricks Jobs** | Orchestrates pipeline runs, synced table setup, and permission grants |
| **Databricks Asset Bundles (DABs)** | Infrastructure-as-code for multi-environment deployment |
| **OpenTelemetry Integration** | Auto-instruments the FastAPI backend for self-observability |

---

## Dashboard Panels

### Service Dashboard
Grid of health cards showing every discovered service with real-time latency, error rate, and request volume. Click any card to drill into detailed metrics.

### Dependency Map
Interactive D3.js force-directed graph of service-to-service call relationships. Node color indicates health status, edge thickness represents call volume. Click a node for a detail panel with metrics and upstream/downstream neighbors.

### Services List
Sortable, searchable table view of all services with columns for latency, error rate, request count, and health status. Useful for batch triage and comparison.

### Metrics Explorer
Time-series charts for P50/P95/P99 latency, request duration, error counts, and throughput. Configurable time ranges (5m, 1h, 1d, 1w) with historical baseline overlays.

### Logs View
Structured log explorer with severity timeline, advanced search syntax, service filtering, and expandable JSON attribute panels. Correlates directly to traces and metrics on the same timeline.

### Traces View
Distributed trace browser listing traces by duration, span count, and services involved. Click any trace to open the waterfall analysis.

### Trace Waterfall
Span-level waterfall visualization showing the full request path across services. Highlights errors, latency bottlenecks, and service boundaries with timing breakdowns.

---

## Quickstart

### Prerequisites

- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html) v0.265.0+
- A Databricks workspace with Unity Catalog enabled
- ZeroBus OTEL collector configured to ingest OpenTelemetry data into bronze-layer Delta tables
- A Lakebase (managed PostgreSQL) instance

### 1. Clone and configure

```bash
git clone <repo-url> && cd o11yApp

# Edit bundle variables for your environment
# Update catalog_name, schema_name, database_instance_name, warehouse_id
vim databricks.yml
```

### 2. Deploy with Databricks Asset Bundles

```bash
# Authenticate to your workspace
databricks auth login --host https://<workspace-url>

# Validate the bundle configuration
databricks bundle validate -t dev

# Deploy all resources (app, pipelines, jobs)
databricks bundle deploy -t dev
```

### 3. Run the setup job

The `full_pipeline_setup` job provisions the entire backend in the correct order:

```bash
# Trigger the full setup job
databricks bundle run full_pipeline_setup -t dev
```

This job executes the following task graph:

```
run_silver_pipeline
        |
        ├──> run_gold_pipeline ──┐
        |                        ├──> sync_service_dependencies
        └──> setup_synced_tables ├──> sync_traces_assembled
                        |        
                        └──> grant_app_permissions
```

**What it does:**
1. Runs the Silver DLT pipeline (flatten and enrich raw OTel data)
2. Runs the Gold DLT pipeline (aggregate dependencies, metrics, baselines)
3. Creates Lakebase synced tables (reverse ETL from Delta to PostgreSQL)
4. Syncs gold-layer tables (service dependencies, assembled traces)
5. Grants the Databricks App service principal access to Lakebase

### 4. Open the app

```bash
# Check app status and get the URL
databricks apps get o11y-jmr --output json | jq -r '.url'
```

Navigate to the URL in your browser. Databricks OAuth handles authentication automatically.

### Scheduled refresh

The `dev_job` runs on a configurable schedule (default: every 30 minutes) to keep data fresh:

```
Silver pipeline -> Gold pipeline -> Sync dependencies -> Sync traces
```

Adjust the schedule in `databricks.yml` under the target's `dev_job` resource.

---

## Local Development

```bash
# Install dependencies and configure environment
./setup.sh

# Start frontend (5173) + backend (8000) with hot reload
nohup ./watch.sh > /tmp/databricks-app-watch.log 2>&1 &

# View logs
tail -f /tmp/databricks-app-watch.log

# Format code
./fix.sh

# Stop dev servers
kill $(cat /tmp/databricks-app-watch.pid)
```

---

## Project Structure

```
o11yApp/
├── server/                  # FastAPI backend
│   ├── app.py               # Entry point + middleware
│   ├── routers/             # API endpoints (services, deps, logs, traces, metrics)
│   └── services/            # Lakebase connection manager, data services
├── client/                  # React TypeScript frontend
│   ├── src/pages/           # Dashboard, DependencyMap, Metrics, Logs, Traces, etc.
│   └── src/components/      # Reusable charts, tables, panels (D3, Recharts, shadcn)
├── pipeline/
│   ├── notebooks/dlt/       # Silver streaming + Gold batch DLT notebooks
│   ├── notebooks/quality/   # Data validation notebooks
│   └── scripts/             # Synced table setup/teardown scripts
├── resources/               # DAB resource definitions
│   ├── app.yml              # Databricks App config
│   ├── pipelines.yml        # DLT pipeline definitions
│   └── pipeline_jobs.yml    # Job orchestration (setup, dev refresh)
├── databricks.yml           # Asset Bundle root config (dev/dogfood/prod targets)
├── app.yaml                 # App runtime config (command, env vars)
└── docs/                    # Product requirements and API reference
```

---

## License

Internal use.
