# Metrics Schema Analysis and Required Fixes

## Schema Comparison

### New Schema (jmr_demo.zerobus_sdp.metrics_1min_synced)
```
1. name - STRING
2. service_name - STRING
3. metric_type - STRING
4. window_start - TIMESTAMP
5. window_end - TIMESTAMP
6. sample_count - LONG
7. avg_value - DOUBLE
8. min_value - DOUBLE
9. max_value - DOUBLE
10. sum_value - DOUBLE
11. ingestion_timestamp - TIMESTAMP
```

### Old Schema (Implied from queries)
The queries expect these additional columns:
- `p50_value` - **MISSING**
- `p95_value` - **MISSING**
- `p99_value` - **MISSING**

## Problems Found

### 1. metrics_kpis.py - Lines 130-132, 144-146, 166-168
**Current Query (BROKEN):**
```sql
SELECT
    to_timestamp(floor(extract(epoch from window_start) / {bucket_seconds}) * {bucket_seconds}) as bucket_time,
    AVG(avg_value) as bucket_avg,
    AVG(p50_value) as bucket_p50,  -- ❌ Column doesn't exist
    AVG(p95_value) as bucket_p95,  -- ❌ Column doesn't exist
    AVG(p99_value) as bucket_p99,  -- ❌ Column doesn't exist
    SUM(sum_value) as bucket_sum,
    SUM(sample_count) as bucket_samples
FROM {LAKEBASE_SCHEMA_NAME}.metrics_1min_synced
```

**Impact:**
- All KPI queries for histogram metrics will fail
- Cannot display p50, p95, p99 percentiles
- Frontend will receive errors when requesting metric data

### 2. Query Usage Locations

**metrics_kpis.py:**
- Line 130-132: Current period query (bucketed data)
- Line 144-146: Aggregation query (sparkline data)
- Line 166-168: Baseline period query (trend calculation)
- Line 217-247: Result formatting (expects percentile data)

**services.py:**
- Line 60: Uses table but not percentile columns ✅ OK

## Solutions

### Option 1: Remove Percentile Support (Recommended)
Since we only have aggregated data (avg, min, max), we cannot accurately calculate percentiles. Remove percentile fields from queries and responses.

**Changes needed:**
1. Remove `p50_value`, `p95_value`, `p99_value` from SQL queries
2. Update response format to only include `avg` for histogram metrics
3. Update frontend to not expect percentile data

### Option 2: Use Approximations (Not Recommended)
Calculate rough approximations:
- p50 ≈ avg_value
- p95 ≈ avg_value + (max_value - avg_value) * 0.8
- p99 ≈ avg_value + (max_value - avg_value) * 0.95

**Problems:**
- Highly inaccurate for skewed distributions
- Misleading to users
- Not statistically valid

### Option 3: Query Raw Metrics (If Available)
If raw, unaggregated metrics exist in another table, query those instead and calculate percentiles on-demand.

**Requirements:**
- Need access to raw metric data table
- Performance impact of calculating percentiles in real-time
- May not scale well for large time ranges

### Option 4: Update Aggregation Schema (Upstream Fix)
Modify the upstream aggregation pipeline to include percentile calculations during aggregation.

**Requirements:**
- Schema change to add p50_value, p95_value, p99_value columns
- Update aggregation logic to calculate percentiles
- Backfill historical data or accept data loss

## Recommended Action Plan

1. **Immediate Fix (Option 1):**
   - Remove percentile columns from queries
   - Update response format to only use avg_value
   - Document that percentiles are not available for pre-aggregated data
   - Deploy fix to restore functionality

2. **Long-term Solution (Option 4):**
   - Work with data engineering to add percentiles to aggregation pipeline
   - Update schema to include p50_value, p95_value, p99_value
   - Once available, restore percentile queries

## Files Requiring Changes

### metrics_kpis.py
- Lines 130-132: Remove p50, p95, p99 from bucketed query
- Lines 144-154: Remove percentile aggregations
- Lines 166-168: Remove p50, p95, p99 from baseline query
- Lines 179-182: Remove baseline percentile calculations
- Lines 213-247: Update response format for histogram metrics

### Frontend (if applicable)
- Update KPI components to not expect percentile data
- Adjust chart rendering for histogram metrics
- Update UI to show only avg values

## Testing Plan

1. **Verify schema access:**
   ```bash
   databricks tables get jmr_demo.zerobus_sdp.metrics_1min_synced --output json | jq '.columns'
   ```

2. **Test query after fix:**
   ```bash
   curl -s http://localhost:8000/api/services/[service-name]/kpis?time_range=1h
   ```

3. **Validate response structure:**
   - Histogram metrics should return only avg values
   - No errors in logs
   - Frontend renders correctly
