# Metrics Schema Fix Summary

## Changes Made

### Schema Analysis
Verified the actual schema in Unity Catalog for `jmr_demo.zerobus_sdp.metrics_1min_synced`:

**Available Columns:**
- `name` - STRING
- `service_name` - STRING
- `metric_type` - STRING
- `window_start` - TIMESTAMP
- `window_end` - TIMESTAMP
- `sample_count` - LONG
- `avg_value` - DOUBLE
- `min_value` - DOUBLE
- `max_value` - DOUBLE
- `sum_value` - DOUBLE
- `ingestion_timestamp` - TIMESTAMP

**Missing Columns (removed from queries):**
- `p50_value` ❌
- `p95_value` ❌
- `p99_value` ❌

## Files Updated

### 1. server/routers/metrics_kpis.py

**Line ~125-156: Current period query**
- ✅ Removed: `AVG(p50_value)`, `AVG(p95_value)`, `AVG(p99_value)`
- ✅ Added: `AVG(min_value)`, `AVG(max_value)`
- ✅ Updated sparkline arrays to use min/max instead of percentiles

**Line ~162-185: Baseline period query**
- ✅ Removed: `AVG(p50_value)`, `AVG(p95_value)`, `AVG(p99_value)`
- ✅ Added: `AVG(min_value)`, `AVG(max_value)`

**Line ~213-248: Response format for histogram metrics**
- ✅ Changed: `percentiles` → `statistics`
- ✅ Removed: `p50`, `p95`, `p99` fields
- ✅ Updated: Now returns `avg`, `min`, `max` with trends and timeseries

## Impact

### API Response Changes
**Before (broken):**
```json
{
  "metrics_by_type": {
    "histogram": {
      "http.server.duration": {
        "percentiles": {
          "p50": {"value": 123.45, "trend": "up", "timeseries": [...]},
          "p95": {"value": 456.78, "trend": "stable", "timeseries": [...]},
          "p99": {"value": 789.01, "trend": "down", "timeseries": [...]},
          "avg": {"value": 234.56, "trend": "up", "timeseries": [...]}
        }
      }
    }
  }
}
```

**After (working):**
```json
{
  "metrics_by_type": {
    "histogram": {
      "http.server.duration": {
        "statistics": {
          "avg": {"value": 234.56, "trend": "up", "timeseries": [...]},
          "min": {"value": 12.34, "trend": "stable", "timeseries": [...]},
          "max": {"value": 789.01, "trend": "down", "timeseries": [...]}
        }
      }
    }
  }
}
```

### Frontend Impact
If the frontend expects `percentiles` field:
- Update components to use `statistics` instead
- Adjust charts to display avg/min/max instead of p50/p95/p99
- Update any TypeScript interfaces

### Gauge and Sum Metrics
✅ No changes needed - these metric types don't use percentiles

## Testing Recommendations

1. **Test the endpoint:**
   ```bash
   curl -s http://localhost:8000/api/services/<service-name>/kpis?time_range=1h | jq
   ```

2. **Verify no errors:**
   ```bash
   tail -f /tmp/databricks-app-watch.log | grep -i error
   ```

3. **Check response structure:**
   - Histogram metrics should have `statistics` field
   - Statistics should contain `avg`, `min`, `max`
   - Each statistic should have `value`, `trend`, `timeseries`

## Next Steps

### Immediate
- ✅ Queries fixed to match schema
- ⚠️ Frontend may need updates if it expects `percentiles`

### Future Enhancements
If true percentiles are needed:
1. Update upstream aggregation pipeline to calculate percentiles
2. Add `p50_value`, `p95_value`, `p99_value` columns to schema
3. Revert to percentile-based queries
4. Update frontend to display percentiles again

## Documentation
- Created: `claudedocs/METRICS_SCHEMA_ANALYSIS.md` - Detailed analysis
- Created: `claudedocs/METRICS_SCHEMA_FIX_SUMMARY.md` - This summary
