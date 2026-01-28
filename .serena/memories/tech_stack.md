# Technology Stack

## Backend
- **Language**: Python 3.12+
- **Framework**: FastAPI
- **Package Manager**: `uv` (modern Python package manager)
- **Database**: Lakebase (PostgreSQL) via Databricks SDK
- **Key Libraries**:
  - `databricks-sdk` - Databricks workspace integration
  - `psycopg2` - PostgreSQL driver
  - `pydantic` - Data validation
  - `fastapi` - Web framework

## Frontend
- **Language**: TypeScript
- **Framework**: React 18
- **Build Tool**: Vite
- **Package Manager**: Bun
- **UI Library**: shadcn/ui with Radix UI primitives
- **Styling**: Tailwind CSS
- **State Management**: React Query (TanStack Query)
- **Key Libraries**:
  - `react-query` - Server state management
  - `d3` - Data visualization
  - `lucide-react` - Icons
  - `recharts` - Charts

## Development Tools
- **Python Formatter**: ruff
- **Python Linter**: ruff
- **Python Type Checker**: ty
- **TypeScript Formatter**: prettier
- **TypeScript Linter**: ESLint
- **Git**: Version control
- **Databricks CLI**: App deployment and management

## APIs & Integration
- **OpenAPI**: Auto-generated from FastAPI
- **TypeScript Client**: Auto-generated from OpenAPI spec
- **Databricks SDK**: Workspace, SQL, and database operations
- **OAuth**: Databricks Apps authentication

## Infrastructure
- **Platform**: Databricks Apps
- **Database**: Lakebase (Databricks-hosted PostgreSQL)
- **Unity Catalog**: Data governance and permissions
- **Asset Bundles**: Deployment configuration
