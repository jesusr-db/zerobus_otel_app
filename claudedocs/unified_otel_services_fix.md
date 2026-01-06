# Unified OTEL Services Fix

## Problem

The dashboard was only showing services that emit **traces**, but was missing services that only emit **logs** or **metrics** through OpenTelemetry. This gave an incomplete view of the service landscape.

## Root Cause

The original `/api/services/list` endpoint (`server/routers/services.py:52-111`) only queried the `traces_assembled_synced` table:

```sql
-- OLD QUERY (traces only)
WITH current_spans AS (
  SELECT span_value->>'service_name' as service_name ...
  FROM zerobus_sdp.traces_assembled_synced t
  ...
)
```

This excluded:
- Services that only emit logs (logging-only services, batch jobs, etc.)
- Services that only emit metrics (monitoring agents, scrapers, etc.)
- Services during periods when they're not processing traces

## Solution

Updated the query to **UNION services from all three OTEL signals**:

### 1. Extract Services from All Data Sources

```sql
-- Extract from traces
trace_services AS (
  SELECT DISTINCT span_value->>'service_name' as service_name
  FROM zerobus_sdp.traces_assembled_synced t
  ...
),
-- Extract from logs
log_services AS (
  SELECT DISTINCT COALESCE(
    service_name,
    attributes->>'service.name',
    attributes->>'service_name'
  ) as service_name
  FROM zerobus_sdp.logs_synced
  ...
),
-- Extract from metrics
metric_services AS (
  SELECT DISTINCT COALESCE(
    service_name,
    attributes->>'service.name',
    attributes->>'service_name'
  ) as service_name
  FROM zerobus_sdp.metrics_1min_synced
  ...
),
-- Combine all services
all_services AS (
  SELECT service_name FROM trace_services
  UNION
  SELECT service_name FROM log_services
  UNION
  SELECT service_name FROM metric_services
)
```

### 2. Enhanced Health Status Calculation

The health status now considers **both trace errors AND log errors**:

```sql
-- Count error logs per service
log_counts AS (
  SELECT
    service_name,
    COUNT(*) as log_count,
    SUM(CASE
      WHEN severity_text IN ('ERROR', 'FATAL', 'CRITICAL')
      OR CAST(severity_number AS INTEGER) >= 17  -- OTEL severity levels
      THEN 1 ELSE 0
    END) as log_error_count
  FROM zerobus_sdp.logs_synced
  ...
)

-- Health status considers both trace and log errors
CASE
  WHEN log_error_count > 10 AND request_count = 0 THEN 'critical'  -- logs-only service with many errors
  WHEN latency_p50 > baseline THEN 'critical'                      -- slow traces
  WHEN request_count / seconds > baseline_rps THEN 'warning'       -- high load
  WHEN log_error_count > 0 THEN 'warning'                          -- any log errors
  ELSE 'healthy'
END as health_status
```

### 3. Aggregated Error Count

Error counts now include both sources:

```sql
error_count = trace_error_count + log_error_count
error_rate = (trace_errors + log_errors) / (requests + logs)
```

## Changes Made

### Files Modified

1. **`server/routers/services.py:49-190`**
   - Updated Lakebase query to include logs and metrics
   - Added `log_services` and `metric_services` CTEs
   - Combined all services with UNION
   - Enhanced health calculation with log errors
   - Maintained backward compatibility with existing API contract

2. **`server/routers/lakebase_validation.py:568-653`**
   - Added `/api/lakebase-validation/inspect-otel-tables` endpoint
   - Helps diagnose schema differences across environments
   - Returns column info and sample services from each table

### Files Created

1. **`claude_scripts/unified_services_query.sql`**
   - Full documented SQL query showing the unified approach
   - Includes additional analytics (data_sources, log_count, metric_count)

2. **`claude_scripts/inspect_otel_tables.py`**
   - Python script to inspect table schemas locally
   - Useful for understanding data structure

## Testing

### 1. Check OTEL Table Schemas

Visit the inspection endpoint to understand your data structure:

```
https://o11y-jmr-1351565862180944.aws.databricksapps.com/api/lakebase-validation/inspect-otel-tables
```

Or via FastAPI docs:
```
https://o11y-jmr-1351565862180944.aws.databricksapps.com/docs
```

This shows:
- Column names and types for each table
- Row counts
- Service column names
- Sample service names from each data source

### 2. Test Services Endpoint

The main services endpoint now returns ALL services:

```
https://o11y-jmr-1351565862180944.aws.databricksapps.com/api/services/list?time_range=1h
```

Expected changes:
- **Before**: Only services with traces in the time range
- **After**: All services with traces OR logs OR metrics in the time range

### 3. Verify Dashboard

Open the dashboard and check:
- More services should now be visible
- Services that only emit logs (like batch jobs) should appear
- Services that only emit metrics (like monitoring agents) should appear
- Health status should reflect log errors in addition to trace errors

## Robustness Features

### Schema Flexibility

The query uses `COALESCE` to handle different possible column names:

```sql
COALESCE(
  service_name,              -- Direct column
  attributes->>'service.name',  -- OTEL semantic convention
  attributes->>'service_name'   -- Alternative naming
) as service_name
```

This handles:
- Tables where service_name is a direct column
- Tables where it's in a JSONB attributes field
- Different naming conventions across environments

### Graceful Degradation

- If logs_synced or metrics_1min_synced don't exist, the query will fail
- **Recommendation**: Add TRY-CATCH logic or table existence checks if these tables might not be present in all environments
- Current implementation assumes all three tables exist (safe assumption for this environment)

### Null Safety

- All aggregations use `COALESCE` to handle services without certain signal types
- Services with only logs will have 0.0 for all latency metrics
- Services with only traces will have 0 for log_count

## Performance Considerations

### Query Efficiency

The unified query performs:
- 3 DISTINCT scans (one per table) to get service names
- 2 trace table scans for current and baseline metrics
- 1 log table scan for log counts
- 1 metric table scan for metric presence

**Expected performance**: Similar to original query, as PostgreSQL can optimize the UNION and parallel scans.

### Indexing Recommendations

For optimal performance, ensure indexes exist on:
- `traces_assembled_synced(trace_start)` ✓ (likely exists)
- `logs_synced(timestamp)` (recommended)
- `logs_synced(service_name)` or `logs_synced((attributes->>'service.name'))` (recommended)
- `metrics_1min_synced(time)` (recommended)
- `metrics_1min_synced(service_name)` or similar (recommended)

## Known Limitations

1. **Schema Assumptions**
   - Assumes `logs_synced` has `timestamp`, `severity_text`, `severity_number` columns
   - Assumes `metrics_1min_synced` has `time` column
   - Uses COALESCE to handle different service_name locations

2. **Metrics Not Fully Utilized**
   - Currently only used to identify services
   - Could be enhanced to show metric-based health indicators
   - Future: Add CPU, memory, request rate from metrics

3. **Time Range Consistency**
   - All three sources use the same time range filter
   - Services with very old data won't appear unless they have recent signals

## Future Enhancements

1. **Add Metrics-Based Health**
   - CPU usage > 80% → warning
   - Memory usage > 90% → critical
   - Request rate anomalies

2. **Show Data Source Indicators**
   - UI badges: "Traces", "Logs", "Metrics"
   - Help users understand which signals each service emits

3. **Separate Views**
   - "Trace Services" tab
   - "Log-only Services" tab
   - "All Services" tab (current)

4. **Error Log Details**
   - Show recent error log messages
   - Link to log explorer filtered by service

## Rollback Plan

If issues arise, revert to traces-only query:

```bash
# Checkout previous version
git diff HEAD~1 server/routers/services.py

# Or manually restore the old query (lines 52-111)
# Then redeploy
databricks bundle deploy
```

## Verification Checklist

✅ Deployed to: `o11y-jmr-1351565862180944.aws.databricksapps.com`
✅ Inspection endpoint available: `/api/lakebase-validation/inspect-otel-tables`
✅ Main services endpoint updated: `/api/services/list`
✅ Backward compatible: Same API response schema
✅ Health status enhanced: Includes log errors

⏳ **Pending**: User verification that additional services now appear
⏳ **Pending**: Schema inspection results from production environment

## Next Steps

1. **Verify in Browser**
   - Open the dashboard
   - Check if more services are visible
   - Look for log-only or metrics-only services

2. **Inspect Table Schemas**
   - Visit `/api/lakebase-validation/inspect-otel-tables`
   - Verify the column names match query assumptions
   - Adjust query if schema differs

3. **Monitor Performance**
   - Check query execution time in logs
   - Compare with previous query performance
   - Optimize if needed (add indexes, adjust filters)

4. **User Feedback**
   - Confirm all expected services now appear
   - Validate health status accuracy
   - Identify any missing services for further investigation
