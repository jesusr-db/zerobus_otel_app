# Current Project State

## Active Branch
**Branch**: `no-otel`
**Created From**: `lakebasesync`
**Purpose**: Remove all OpenTelemetry instrumentation from codebase

## Recent Changes (January 2026)

### OpenTelemetry Removal (Current Branch)
**Status**: ✅ Completed
- Deleted `server/observability/telemetry.py` (237 lines)
- Removed `server/observability/` directory
- Removed telemetry setup from `server/app.py`
- Removed OTEL environment variables from `app.yml`:
  - `OTEL_SERVICE_NAME`
  - `OTEL_CATALOG`
  - `OTEL_SCHEMA`
  - `OTEL_TABLE_PREFIX`
  - `DATABRICKS_OTEL_TOKEN`
  - `DATABRICKS_HOST`
- Removed `otel-token` secret resource from `resources/app.yml`
- Application now runs without any telemetry instrumentation

### Databricks Secrets Configuration
**Status**: ✅ Resolved (documented in backlog)
- Fixed incorrect secrets reference format in Asset Bundles
- Changed from `value: {{secrets.xxx}}` to `valueFrom: resource-name`
- Documented in `docs/PROJECT_PLAN.md` backlog as Issue #001

### Dependency Graph Fix
**Status**: ✅ Completed
- Fixed table name: `service_dependencies` → `service_dependencies_synced`
- Fixed PostgreSQL interval syntax: `INTERVAL * 2` → `INTERVAL + INTERVAL`
- Fixed column name case: `errorrate` → `"errorRate"` (quoted for case preservation)
- Updated both Lakebase and Warehouse backends

### Pending Deployment
**Status**: ⏳ Not Deployed
- Changes are local on `no-otel` branch
- Need to build frontend and deploy to Databricks Apps
- Commands:
  ```bash
  cd client && bun run build
  databricks bundle deploy --target dev
  ```

## Current Configuration

### Data Backend
- **Type**: Lakebase (PostgreSQL)
- **Environment Variable**: `DATA_BACKEND=lakebase`
- **Database**: `zerobus_sdp`
- **Instance**: `zerobus-dev`
- **Host**: `instance-fbdab8c4-86f6-400a-ac42-632a91017360.database.cloud.databricks.com`

### Key Tables
- `traces_assembled_synced` - Distributed traces with JSONB span details
- `service_dependencies_synced` - Service-to-service dependencies
- `metrics_1min_synced` - Metrics aggregated per minute
- `logs_synced` - Application logs

### Databricks App
- **Name**: `o11y-jmr`
- **URL**: `https://o11y-jmr-1351565862180944.aws.databricksapps.com`
- **Status**: Deployed (older version without OTEL removal)
- **Compute**: MEDIUM
- **State**: RUNNING

## Known Issues / Technical Debt

### Issue #002: Lakebase Host Auto-Detection
**Priority**: P0
**Status**: BACKLOG
- Currently hardcoded in `app.yml:21-22`
- Blocks deployment automation
- Should auto-detect via Databricks SDK
- See `docs/PROJECT_PLAN.md` for full details

### Metrics View Aggregation
**Status**: Open
- METRICS view showing last events instead of aggregating by timeframe
- Needs investigation and fix

### Waterfall Visualization
**Status**: Previously had bugs, may need verification
- Implementation in `client/src/pages/TracingAnalysisView.tsx`
- Backend: `/api/traces/waterfall/{trace_id}`

## Git Status
```
On branch no-otel
Changes not staged for commit:
  modified:   app.yml
  modified:   resources/app.yml
  modified:   server/app.py
  deleted:    server/observability/telemetry.py
```

## Development Status
- ✅ Codebase loaded into Serena MCP
- ✅ Onboarding complete
- ⏳ Changes ready for deployment
- ⏳ Frontend needs rebuild
- ⏳ Backend changes ready for deploy

## Next Steps
1. Rebuild frontend: `cd client && bun run build`
2. Deploy to Databricks: `databricks bundle deploy --target dev`
3. Monitor deployment logs
4. Verify dependency graph works correctly
5. Test all endpoints
6. Commit changes with descriptive message
