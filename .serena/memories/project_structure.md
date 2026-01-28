# Project Structure

## Root Directory Layout

```
o11yApp/
├── server/              # Python FastAPI backend
├── client/              # React TypeScript frontend
├── scripts/             # Utility scripts
├── resources/           # Databricks bundle configuration
├── docs/                # Documentation
├── notebooks/           # Databricks notebooks (if any)
├── claude_scripts/      # Temporary test scripts created by Claude
├── claudedocs/          # Claude-generated documentation
├── .databricks/         # Databricks CLI configuration
├── .venv/               # Python virtual environment
├── __pycache__/         # Python bytecode cache
├── app.yml              # Databricks App runtime configuration
├── databricks.yml       # Databricks Asset Bundle configuration
├── pyproject.toml       # Python dependencies
├── uv.lock              # Python dependency lock file
├── requirements.txt     # Generated Python requirements
├── CLAUDE.md            # Development guide for Claude
└── .env.local           # Local environment variables (not committed)
```

## Backend Structure (`server/`)

```
server/
├── app.py               # FastAPI application entry point
├── config.py            # Configuration and environment variables
├── models/              # Pydantic models for request/response
│   ├── observability.py # Traces, metrics, dependencies models
│   ├── logs.py          # Log models
│   └── user.py          # User models
├── routers/             # API route handlers
│   ├── __init__.py      # Router registration
│   ├── dependencies.py  # Dependency graph endpoints
│   ├── services.py      # Service metrics and health
│   ├── traces.py        # Trace analysis endpoints
│   ├── logs.py          # Log aggregation and search
│   ├── metrics_kpis.py  # KPI metrics
│   ├── user.py          # User info endpoints
│   ├── warehouse.py     # SQL Warehouse operations
│   └── lakebase_validation.py  # Lakebase connectivity tests
└── services/            # Business logic and data access
    ├── warehouse_manager.py  # SQL Warehouse data access
    ├── lakebase_manager.py   # Lakebase (PostgreSQL) data access
    └── sql_converter.py      # Spark SQL to PostgreSQL converter
```

## Frontend Structure (`client/`)

```
client/
├── src/
│   ├── App.tsx          # Main application component
│   ├── main.tsx         # React entry point
│   ├── index.css        # Global styles
│   ├── pages/           # Page components (routes)
│   │   ├── DashboardView.tsx       # Service health dashboard
│   │   ├── ServicesListView.tsx    # Service list
│   │   ├── DependencyMapView.tsx   # Dependency graph
│   │   ├── TracesView.tsx          # Trace list
│   │   ├── TracingAnalysisView.tsx # Waterfall visualization
│   │   ├── LogsView.tsx            # Log viewer
│   │   ├── MetricsView.tsx         # Metrics dashboard
│   │   └── WelcomePage.tsx         # Landing page
│   ├── components/      # Reusable components
│   │   ├── ui/          # shadcn/ui components
│   │   ├── ServiceDetailPanel.tsx  # Service details
│   │   ├── TraceDetailPanel.tsx    # Trace details
│   │   ├── LogDetailsPanel.tsx     # Log details
│   │   ├── MetricCards.tsx         # Metric display cards
│   │   └── ...          # Other components
│   ├── types/           # TypeScript type definitions
│   │   ├── service.ts   # Service types
│   │   ├── trace.ts     # Trace types
│   │   └── logs.ts      # Log types
│   ├── fastapi_client.ts  # Auto-generated API client
│   └── lib/             # Utility functions
│       └── utils.ts     # Helper functions
├── public/              # Static assets
├── build/               # Production build output
├── package.json         # Frontend dependencies
├── tsconfig.json        # TypeScript configuration
├── vite.config.ts       # Vite configuration
└── tailwind.config.js   # Tailwind CSS configuration
```

## Scripts (`scripts/`)

```
scripts/
├── make_fastapi_client.py  # Generate TypeScript client from OpenAPI
└── ...                     # Other utility scripts
```

## Resources (`resources/`)

```
resources/
├── app.yml                      # Databricks App bundle configuration
└── grant_permissions_job.yml    # Job for granting permissions
```

## Documentation (`docs/`)

```
docs/
├── PROJECT_PLAN.md          # Project roadmap and backlog
├── VALIDATION_RESULTS.md    # Lakebase validation results
├── databricks_apis/         # Databricks API documentation
│   ├── databricks_sdk.md    # SDK usage patterns
│   ├── mlflow_genai.md      # MLflow GenAI guide
│   ├── model_serving.md     # Model serving guide
│   └── workspace_apis.md    # Workspace operations
├── product.md               # Product requirements (if exists)
└── design.md                # Technical design (if exists)
```

## Configuration Files

### Root Level
- `app.yml` - Databricks App runtime config (env vars, resources)
- `databricks.yml` - Asset Bundle config (targets, variables)
- `pyproject.toml` - Python project metadata and dependencies
- `uv.lock` - Locked Python dependencies
- `requirements.txt` - Generated Python requirements (for deployment)
- `.env.local` - Local environment variables (not committed)
- `.gitignore` - Git ignore patterns
- `.bundleignore` - Databricks bundle ignore patterns
- `.python-version` - Python version specification

### Frontend
- `client/package.json` - Frontend dependencies
- `client/tsconfig.json` - TypeScript configuration
- `client/vite.config.ts` - Vite build configuration
- `client/tailwind.config.js` - Tailwind CSS configuration
- `client/components.json` - shadcn/ui configuration

## Key Entry Points

1. **Backend**: `server/app.py` - FastAPI app initialization
2. **Frontend**: `client/src/main.tsx` - React app initialization
3. **Development**: `./watch.sh` - Start dev servers
4. **Deployment**: `./deploy.sh` - Deploy to Databricks Apps
5. **Setup**: `./setup.sh` - Environment setup

## Data Flow

```
User Request
    ↓
Frontend (React) at localhost:5173
    ↓
API Call via auto-generated client
    ↓
Backend (FastAPI) at localhost:8000
    ↓
Data Manager (Lakebase or Warehouse)
    ↓
Databricks Database (PostgreSQL or SQL Warehouse)
    ↓
Response back to Frontend
    ↓
Display in UI
```
