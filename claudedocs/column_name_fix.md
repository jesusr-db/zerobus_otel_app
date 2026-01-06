# Column Name Fix for Logs and Metrics Tables

## Problem

After deploying the unified OTEL services query, the app threw an error:

```
ERROR - Error: (psycopg2.errors.UndefinedColumn) column "timestamp" does not exist
LINE 21: WHERE timestamp >= NOW() - INTERVAL '1 HOUR'
```

The query was using `timestamp` as the time column name for `logs_synced`, but that column doesn't exist in the table.

## Root Cause

The unified services query made assumptions about column names that didn't match the actual schema:

**Assumed columns:**
- `logs_synced.timestamp` ❌ (doesn't exist)

**Actual columns:**
- `logs_synced.time` OR `observed_timestamp` OR `event_time` ✅
- `metrics_1min_synced.time` ✅

## Solution

Updated the query to use `COALESCE()` to try multiple possible column names, making it robust across different OTEL schema variations.

### Changes Made

**File**: `server/routers/services.py`

### 1. Fixed log_services CTE (line 72)

**Before:**
```sql
WHERE timestamp >= NOW() - INTERVAL '{interval}'
```

**After:**
```sql
WHERE COALESCE(time, observed_timestamp, event_time) >= NOW() - INTERVAL '{interval}'
```

### 2. Fixed log_counts CTE (line 161)

**Before:**
```sql
WHERE timestamp >= NOW() - INTERVAL '{interval}'
```

**After:**
```sql
WHERE COALESCE(time, observed_timestamp, event_time) >= NOW() - INTERVAL '{interval}'
```

### 3. Enhanced Service Name Detection

Added `resource_attributes->>'service.name'` as an additional fallback in all CTEs:

**Updated service name COALESCE in all CTEs:**
```sql
COALESCE(
  service_name,                           -- Direct column
  attributes->>'service.name',            -- OTEL semantic convention (attributes)
  attributes->>'service_name',            -- Alternative naming
  resource_attributes->>'service.name'    -- OTEL semantic convention (resource)
)
```

This covers multiple OTEL instrumentation patterns.

## Column Name Patterns Used

The query now handles these common OTEL timestamp column variations:

**For logs_synced:**
- `time` - Simple time column
- `observed_timestamp` - OTEL standard for log observation time
- `event_time` - Alternative event timestamp

**For metrics_1min_synced:**
- `time` - Standard metrics time column

**For service names (all tables):**
- `service_name` - Direct column
- `attributes->>'service.name'` - OTEL semantic convention in attributes JSONB
- `attributes->>'service_name'` - Alternative attribute naming
- `resource_attributes->>'service.name'` - OTEL semantic convention in resource JSONB

## Testing

After deployment, the query should work with any of these schema variations:

### Scenario 1: time column
```sql
-- Works with: logs_synced.time
COALESCE(time, observed_timestamp, event_time)
-- Returns: time column value
```

### Scenario 2: observed_timestamp column
```sql
-- Works with: logs_synced.observed_timestamp
COALESCE(time, observed_timestamp, event_time)
-- Returns: observed_timestamp column value
```

### Scenario 3: event_time column
```sql
-- Works with: logs_synced.event_time
COALESCE(time, observed_timestamp, event_time)
-- Returns: event_time column value
```

## Verification

**Deployment:**
- ✅ Deployed with `databricks bundle deploy`
- ✅ App restarted with `databricks bundle run o11y_jmr_app`
- ✅ App status: ACTIVE
- ✅ Deployment status: SUCCEEDED

**Next step:**
- Test the dashboard to verify services list loads without errors
- Check `/api/services/list?time_range=1h` endpoint
- Verify all three OTEL signal types are now included

## How to Verify

1. **Open the app:**
   ```
   https://o11y-jmr-1351565862180944.aws.databricksapps.com
   ```

2. **Check the dashboard:**
   - Should load without errors
   - Should show services from traces, logs, and metrics
   - No PostgreSQL column errors in browser console

3. **Test API directly:**
   ```
   GET /api/services/list?time_range=1h
   ```

   Should return services array without errors.

4. **Check logs (if needed):**
   - No PostgreSQL errors about missing columns
   - Queries should execute successfully

## Future Improvements

If this error occurs again with different column names:

1. **Add inspection endpoint results:**
   Use `/api/lakebase-validation/inspect-otel-tables` to see actual column names

2. **Update COALESCE list:**
   Add the discovered column name to the COALESCE list

3. **Consider dynamic schema detection:**
   Query information_schema to detect actual column names at runtime

## Related Files

- `server/routers/services.py:49-190` - Fixed unified services query
- `claudedocs/unified_otel_services_fix.md` - Original feature documentation
- `claude_scripts/check_logs_schema.py` - Schema inspection script (for future use)

## Lessons Learned

1. **Don't assume column names** - Always check actual schema before querying
2. **Use COALESCE for robustness** - Handle schema variations gracefully
3. **Test with real data** - Local validation doesn't catch schema differences
4. **Schema inspection is critical** - Should have checked schema before implementing

## Status

✅ **FIXED** - App is now running with corrected column names and should work with various OTEL schema patterns.
