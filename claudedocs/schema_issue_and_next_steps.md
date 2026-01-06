# Schema Issue and Next Steps

## What Happened

We attempted to add logs and metrics to the services query but encountered **column name mismatches** across multiple attempts:

1. ❌ **First attempt**: Assumed `logs_synced.timestamp` → Column doesn't exist
2. ❌ **Second attempt**: Tried `COALESCE(time, observed_timestamp, event_time)` → None exist
3. ❌ **Third attempt**: Added `resource_attributes` → Column doesn't exist

**Root cause**: We don't know the actual schema of `logs_synced` and `metrics_1min_synced` tables.

## Current Status

✅ **Reverted to working traces-only query**
- App is now RUNNING and functional
- Dashboard shows services from traces only
- Original functionality restored

## What We Need

To properly add logs and metrics support, we need to **inspect the actual table schemas** to find:

### For `logs_synced` table:
- What is the **timestamp column name**? (e.g., `log_timestamp`, `logged_at`, `event_timestamp`, etc.)
- What is the **service name column name**? (e.g., `service_name`, nested in JSONB, etc.)
- What is the **severity column name**? (e.g., `severity`, `log_level`, `severity_text`, etc.)

### For `metrics_1min_synced` table:
- What is the **timestamp column name**? (e.g., `time`, `metric_time`, `timestamp`, etc.)
- What is the **service name column name**?
- What columns contain the actual metric values?

## How to Inspect Schema

### Option 1: Use the Inspection Endpoint (Recommended)

Visit this endpoint in your browser (requires login):
```
https://o11y-jmr-1351565862180944.aws.databricksapps.com/api/lakebase-validation/inspect-otel-tables
```

This will show:
- All column names and types
- Sample service names from each table
- Row counts

### Option 2: Query Directly

If you have database access, run:

```sql
-- Check logs_synced schema
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'zerobus_sdp'
  AND table_name = 'logs_synced'
ORDER BY ordinal_position;

-- Check metrics_1min_synced schema
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'zerobus_sdp'
  AND table_name = 'metrics_1min_synced'
ORDER BY ordinal_position;

-- Sample data from logs
SELECT * FROM zerobus_sdp.logs_synced LIMIT 1;

-- Sample data from metrics
SELECT * FROM zerobus_sdp.metrics_1min_synced LIMIT 1;
```

## Next Steps

Once we have the actual schema:

### Step 1: Update Query Template

Create the correct query with actual column names:

```sql
-- Example template (will need actual column names)
log_services AS (
  SELECT DISTINCT
    <actual_service_name_column> as service_name
  FROM zerobus_sdp.logs_synced
  WHERE <actual_timestamp_column> >= NOW() - INTERVAL '{interval}'
    AND <actual_service_name_column> IS NOT NULL
)
```

### Step 2: Test Query Locally

Before deploying, test the query using the inspection endpoint or direct database access.

### Step 3: Deploy Updated Query

Once verified, deploy the updated services query.

### Step 4: Verify Dashboard

Check that all three data sources (traces, logs, metrics) now appear.

## Temporary Workaround

For now, the dashboard works with **traces only**. This provides:
- ✅ Service health status
- ✅ Latency metrics (P50, P95, P99)
- ✅ Error rates from traces
- ✅ Request counts
- ❌ Missing: Log-only services
- ❌ Missing: Metrics-only services
- ❌ Missing: Error logs in health calculation

## Files Modified

**Reverted to working state:**
- `server/routers/services.py:49-112` - Traces-only query (working)

**For future reference:**
- `claudedocs/unified_otel_services_fix.md` - Original logs/metrics implementation attempt
- `claudedocs/column_name_fix.md` - Column name troubleshooting
- `claude_scripts/check_logs_schema.py` - Schema inspection script

## Lesson Learned

**Always inspect schema before querying**. Don't assume column names based on:
- OTEL semantic conventions
- Common naming patterns
- Other environment schemas

Each environment may have different:
- Column names
- Data types
- JSONB structure
- Table layouts

## Action Required

**Please inspect the schema** using one of the methods above and provide:
1. Column names for `logs_synced` (especially timestamp and service_name)
2. Column names for `metrics_1min_synced` (especially time and service_name)
3. Sample data structure if columns are JSONB

Once we have this information, I can quickly add logs and metrics support with the correct column names.

## Current App Status

- ✅ **Status**: RUNNING
- ✅ **Deployment**: SUCCEEDED
- ✅ **URL**: https://o11y-jmr-1351565862180944.aws.databricksapps.com
- ✅ **Functionality**: Working (traces only)
- ⏳ **Logs/Metrics**: Pending schema inspection

The app is stable and functional. We can add logs/metrics support once we know the actual schema.
