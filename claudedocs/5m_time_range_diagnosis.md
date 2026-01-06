# 5-Minute Time Range Issue - Diagnosis & Resolution

## Issue Summary
Dashboard shows no data when filtering by "Last 5 minutes" time range, but data appears for longer time ranges (1h, 1d, 1w).

## Root Cause Analysis

### Most Likely Cause: **Data Sync Lag**

The Lakebase backend uses **synced tables** (`traces_assembled_synced`) that are periodically synchronized from the source Unity Catalog tables. If the sync frequency is greater than 5 minutes, the 5m time range query will return no results.

**Evidence:**
- Query works fine for 1h, 1d, 1w time ranges
- Code is correct (verified in `server/routers/services.py:49-111`)
- Query uses proper PostgreSQL interval syntax: `NOW() - INTERVAL '5 minutes'`

### Code Location

**Dashboard Query:** `client/src/pages/DashboardView.tsx:14`
```typescript
const response = await fetch(`/api/services/list?time_range=${timeRange}`, {
  credentials: 'include',
});
```

**Backend Handler:** `server/routers/services.py:39-111`
```python
# Native PostgreSQL query for Lakebase
query = f"""
WITH current_spans AS (
  SELECT
    span_value->>'service_name' as service_name,
    ...
  FROM zerobus_sdp.traces_assembled_synced t
  CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
  WHERE t.trace_start >= NOW() - INTERVAL '{interval}'  # '5 MINUTE' for 5m range
)
...
"""
```

## Diagnosis Steps

### 1. Check Data Freshness (New Endpoint Added)

Test the data freshness endpoint to confirm sync lag:

```bash
# Via browser (requires OAuth login)
https://o11y-jmr-1351565862180944.aws.databricksapps.com/api/lakebase-validation/data-freshness

# Or via API docs
https://o11y-jmr-1351565862180944.aws.databricksapps.com/docs
# Navigate to /api/lakebase-validation/data-freshness and click "Try it out"
```

**Expected Output:**
```json
{
  "current_db_time": "2026-01-06 17:30:00+00:00",
  "most_recent_trace": "2026-01-06 17:15:00+00:00",  # 15 minutes old!
  "data_lag": "0:15:00",  # This is the problem
  "trace_counts": {
    "last_5min": 0,     # ❌ No data in 5m
    "last_1hr": 45000,  # ✅ Data exists in 1h
    "last_1day": 500000,
    "total": 2000000
  },
  "diagnosis": {
    "has_5m_data": false,
    "issue": "No data in last 5 minutes - data sync may be delayed"
  }
}
```

### 2. Check Sync Job Configuration

The sync from Unity Catalog to Lakebase is likely controlled by a scheduled job. Check:

```bash
# Check if there's a sync job configured
databricks jobs list --output json | grep -i "lakebase\|sync"

# Or check the job referenced in resources/grant_permissions_job.yml
```

## Solutions

### Option 1: Increase Sync Frequency (Recommended)

If you control the sync job, increase its frequency to run every 1-5 minutes instead of hourly/daily.

**Trade-offs:**
- ✅ Pro: Dashboard 5m filter will work as expected
- ✅ Pro: More real-time observability data
- ⚠️ Con: Higher compute costs for sync job

### Option 2: Adjust Minimum Time Range in UI

Disable the 5m option if sync lag is > 5 minutes.

**Implementation:** `client/src/contexts/TimeRangeContext.tsx`

```typescript
// Remove "5m" option or add warning
const timeRanges = [
  // { value: "5m", label: "Last 5 minutes" },  // Disabled due to sync lag
  { value: "1h", label: "Last hour" },
  { value: "1d", label: "Last day" },
  { value: "1w", label: "Last week" }
];
```

### Option 3: Add Warning Message for 5m Range

Show a user-friendly message when 5m returns no data.

**Implementation:** Update `client/src/pages/DashboardView.tsx:63-72`

```typescript
{services && services.length === 0 && !isLoading && (
  <div className="flex h-full items-center justify-center">
    <div className="max-w-2xl rounded-lg border border-border bg-card p-6 text-center">
      <div className="text-foreground font-semibold mb-2">No recent data</div>
      <div className="text-sm text-muted-foreground">
        {timeRange === "5m"
          ? "Data sync to Lakebase may be delayed. Try selecting a longer time range like '1 hour'."
          : "No service activity found in the selected time range. Try selecting a longer time range."
        }
      </div>
    </div>
  </div>
)}
```

### Option 4: Use SQL Warehouse for Real-Time Queries

Switch to SQL Warehouse backend for queries requiring real-time data, while using Lakebase for historical analysis.

**Implementation:** Add logic to route short time ranges to warehouse:

```python
# server/routers/services.py:29-36
def get_data_manager(user_token: str, time_range: str):
    # Use warehouse for real-time queries (< 15 minutes)
    if time_range == "5m" and os.getenv("LAKEBASE_SYNC_MINUTES", "15") > "5":
        logger.info("Using SQL Warehouse for real-time 5m query")
        return WarehouseManager(user_token=user_token)
    elif DATA_BACKEND == "lakebase":
        logger.info("Using Lakebase backend")
        return LakebaseManager(user_token=user_token)
    else:
        logger.info("Using SQL Warehouse backend")
        return WarehouseManager(user_token=user_token)
```

## Fixed Issues

✅ **Fixed:** Missing `logger` import in `server/routers/dependencies.py:3,9`
- Added `import logging` and `logger = logging.getLogger(__name__)`
- Deployed successfully

✅ **Added:** Data freshness diagnostic endpoint
- Endpoint: `/api/lakebase-validation/data-freshness`
- Shows current data lag and trace counts by time range
- Deployed successfully

## Next Steps

1. **Test the data freshness endpoint** to confirm sync lag hypothesis
2. **Check sync job configuration** to see current frequency
3. **Choose a solution** based on your requirements and constraints
4. **Implement the chosen solution** and test

## Testing the Fix

After implementing a solution, verify it works:

```bash
# 1. Deploy changes
databricks bundle deploy

# 2. Check data freshness
curl https://o11y-jmr-1351565862180944.aws.databricksapps.com/api/lakebase-validation/data-freshness

# 3. Test dashboard with 5m filter
# Open app in browser and select "Last 5 minutes" from time range dropdown

# 4. Monitor logs
python dba_logz.py https://o11y-jmr-1351565862180944.aws.databricksapps.com --search "5m\|INTERVAL '5" --duration 30
```

## References

- Dashboard component: `client/src/pages/DashboardView.tsx:14`
- Services API handler: `server/routers/services.py:39-186`
- Lakebase manager: `server/services/lakebase_manager.py`
- Migration docs: `docs/LAKEBASE_MIGRATION_COMPLETE.md`
