# Diagnostic Scripts Cleanup

## Summary

Removed all local diagnostic scripts that duplicated functionality now available via FastAPI endpoints.

## Scripts Removed

### claude_scripts/ Directory (Removed Entirely)

1. **check_data_freshness.py**
   - Purpose: Checked data freshness and lag in Lakebase
   - Replaced by: `/api/lakebase-validation/data-freshness`
   - Reason: Local script couldn't run without LAKEBASE_HOST, FastAPI endpoint works from deployed app

2. **inspect_otel_tables.py**
   - Purpose: Inspected schema of logs, metrics, and traces tables
   - Replaced by: `/api/lakebase-validation/inspect-otel-tables`
   - Reason: Schema inspection now available as web API endpoint

3. **check_logs_schema.py**
   - Purpose: Checked specific schema for logs_synced and metrics_1min_synced
   - Replaced by: `/api/lakebase-validation/inspect-otel-tables`
   - Reason: Same functionality, FastAPI endpoint provides better access

### Root-Level Test Scripts

4. **test_5m_issue.py**
   - Purpose: Tested 5-minute time range issue on deployed app
   - Replaced by: Direct browser access to dashboard with time range selector
   - Reason: Issue diagnosed, endpoint testing available via curl/browser

5. **test_data_freshness_deployed.py**
   - Purpose: Tested data freshness diagnostic endpoint on deployed app
   - Replaced by: `/api/lakebase-validation/data-freshness`
   - Reason: Redundant test script for endpoint that's now stable

6. **discover_lakebase_schema.py**
   - Purpose: Connected to Lakebase to list available tables
   - Replaced by: `/api/lakebase-validation/inspect-otel-tables`
   - Reason: Schema discovery now available via FastAPI endpoint

7. **test_5m_data_freshness.py**
   - Purpose: Another data freshness check for 5m issue
   - Replaced by: `/api/lakebase-validation/data-freshness`
   - Reason: Duplicate of check_data_freshness.py

8. **check_5m_issue.py**
   - Purpose: Quick test of data freshness to diagnose 5m dashboard issue
   - Replaced by: `/api/lakebase-validation/data-freshness`
   - Reason: Another duplicate diagnostic script

9. **test_freshness_simple.sh**
   - Purpose: Shell script to test data freshness endpoint with Databricks auth
   - Replaced by: Direct browser access or curl with token
   - Reason: Endpoint is stable and accessible, wrapper script unnecessary

## Scripts Kept

### notebooks/grant_lakebase_permissions.py
- **Status**: KEPT (not removed)
- **Purpose**: Databricks notebook for granting Lakebase permissions to app service principal
- **Reason**: This is infrastructure/setup code, referenced by resources/grant_permissions_job.yml
- **Usage**: Run via Databricks job to grant database permissions

## FastAPI Endpoints Available

All diagnostic functionality is now available via these endpoints:

1. **Data Freshness Diagnostic**
   ```
   GET /api/lakebase-validation/data-freshness
   ```
   - Returns current DB time, most recent trace timestamp, data lag
   - Shows trace counts for different time ranges (5m, 1h, 1d)
   - Provides diagnosis for 5m data issues

2. **OTEL Table Schema Inspection**
   ```
   GET /api/lakebase-validation/inspect-otel-tables
   ```
   - Returns complete schema for all OTEL tables (logs, metrics, traces)
   - Shows column names, data types, nullability
   - Lists sample service names from each table
   - Provides row counts

3. **Lakebase Connection Test**
   ```
   GET /api/lakebase-validation/test-connection
   ```
   - Tests basic connectivity to Lakebase
   - Returns connection status and configuration

4. **Table Query Test**
   ```
   GET /api/lakebase-validation/test-query
   ```
   - Tests querying OTEL tables
   - Returns sample data from traces_assembled_synced

## How to Access Endpoints

All endpoints require authentication via Databricks OAuth:

**In Browser:**
```
https://o11y-jmr-1351565862180944.aws.databricksapps.com/api/lakebase-validation/inspect-otel-tables
```

**With curl:**
```bash
# Get token
TOKEN=$(databricks auth token --host https://e2-demo-field-eng.cloud.databricks.com)

# Call endpoint
curl -H "Authorization: Bearer $TOKEN" \
  https://o11y-jmr-1351565862180944.aws.databricksapps.com/api/lakebase-validation/data-freshness | jq
```

**Via API docs:**
```
https://o11y-jmr-1351565862180944.aws.databricksapps.com/docs
```

## Benefits of Cleanup

1. **Reduced Clutter**: Removed 9 redundant diagnostic scripts
2. **Single Source of Truth**: All diagnostics accessible via FastAPI endpoints
3. **Better Access**: Web API accessible from anywhere, not just local dev environment
4. **Maintainability**: One implementation instead of multiple duplicate scripts
5. **Authentication**: Endpoints use proper OAuth authentication
6. **Documentation**: API docs automatically generated via FastAPI

## Project Structure After Cleanup

```
o11yApp/
├── server/
│   ├── routers/
│   │   ├── lakebase_validation.py  # All diagnostic endpoints
│   │   ├── services.py              # Services list (fixed)
│   │   └── dependencies.py          # Dependencies graph
│   └── services/
│       └── lakebase_manager.py      # Database connection
├── notebooks/
│   └── grant_lakebase_permissions.py  # Infrastructure (kept)
├── scripts/
│   └── make_fastapi_client.py       # Client generation
└── claudedocs/                       # Documentation only
```

## Related Work

This cleanup was done after:
- Implementing unified OTEL services query (traces + logs + metrics)
- Creating FastAPI diagnostic endpoints for data freshness and schema inspection
- Fixing column name issues by inspecting actual table schemas
- Successfully deploying app with all three OTEL signal types

## Status

✅ **Cleanup Complete**: All diagnostic scripts removed
✅ **Functionality Preserved**: All diagnostics available via FastAPI endpoints
✅ **Infrastructure Intact**: Kept notebooks/grant_lakebase_permissions.py for permissions management
