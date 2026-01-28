# Frontend Update Complete - Metrics Schema Migration

## Summary

Successfully updated the frontend to match the new backend metrics schema that uses `statistics` (avg/min/max) instead of `percentiles` (p50/p95/p99).

## Files Updated

### 1. Type Definitions
**File:** `client/src/types/metrics.ts`

**Changes:**
- Updated `HistogramMetric` interface
- Removed: `percentiles: { p50, p95, p99, avg }`
- Added: `statistics: { avg, min, max }`

**Before:**
```typescript
export interface HistogramMetric {
  name: string;
  type: 'histogram';
  percentiles: {
    p50: MetricValue;
    p95: MetricValue;
    p99: MetricValue;
    avg: MetricValue;
  };
}
```

**After:**
```typescript
export interface HistogramMetric {
  name: string;
  type: 'histogram';
  statistics: {
    avg: MetricValue;
    min: MetricValue;
    max: MetricValue;
  };
}
```

### 2. Metric Cards Component
**File:** `client/src/components/MetricCards.tsx`

**Changes:**
- Updated `HistogramCard` to use `statistics` instead of `percentiles`
- Changed labels from "P99/P95/P50/Avg" to "Max/Avg/Min"
- Fixed `sparkline` references to use `timeseries` (correct property name)

**Before:**
```typescript
<MetricRow label="P99" value={metric.percentiles.p99} />
<MetricRow label="P95" value={metric.percentiles.p95} />
<MetricRow label="P50" value={metric.percentiles.p50} />
<MetricRow label="Avg" value={metric.percentiles.avg} />
```

**After:**
```typescript
<MetricRow label="Max" value={metric.statistics.max} />
<MetricRow label="Avg" value={metric.statistics.avg} />
<MetricRow label="Min" value={metric.statistics.min} />
```

### 3. Metrics View Page
**File:** `client/src/pages/MetricsView.tsx`

**Changes:**
- Updated histogram metric display grid from 4 columns to 3 columns
- Changed from displaying P99/P95/P50/Avg to Max/Avg/Min
- Updated chart series to show 3 lines (Max/Avg/Min) instead of 4 (P99/P95/P50/Avg)
- Updated chart colors for better visual distinction

**Before:**
```typescript
<div className="grid grid-cols-2 gap-4 md:grid-cols-4">
  <div>P99: {metric.data.percentiles.p99.value}</div>
  <div>P95: {metric.data.percentiles.p95.value}</div>
  <div>P50: {metric.data.percentiles.p50.value}</div>
  <div>Avg: {metric.data.percentiles.avg.value}</div>
</div>
```

**After:**
```typescript
<div className="grid grid-cols-3 gap-4">
  <div>Max: {metric.data.statistics.max.value}</div>
  <div>Avg: {metric.data.statistics.avg.value}</div>
  <div>Min: {metric.data.statistics.min.value}</div>
</div>
```

### 4. Metrics KPI Panel
**File:** `client/src/components/MetricsKPIPanel.tsx`

**Status:** No changes needed - component passes data through to child components

## Files NOT Changed

### DashboardView.tsx and ServicesListView.tsx
These files display latency percentiles (P50, P95, P99) but they:
- Use data from `/api/services/list` endpoint
- Calculate percentiles from trace spans (traces_silver_synced)
- Are NOT affected by the metrics_1min_synced schema changes
- **Do NOT need updates**

## Visual Changes

### Histogram Metrics Display

**Old Layout:** 4 values in 2x2 or 1x4 grid
```
┌────────┬────────┬────────┬────────┐
│  P99   │  P95   │  P50   │  Avg   │
└────────┴────────┴────────┴────────┘
```

**New Layout:** 3 values in 1x3 grid
```
┌────────┬────────┬────────┐
│  Max   │  Avg   │  Min   │
└────────┴────────┴────────┘
```

### Chart Colors
- **Max:** Red `hsl(0, 84%, 60%)` - Indicates highest values
- **Avg:** Blue `hsl(220, 70%, 60%)` - Standard metric line
- **Min:** Green `hsl(160, 60%, 45%)` - Indicates lowest values

## Build Verification

✅ **Frontend builds successfully:**
```bash
$ bun run build
vite v5.4.19 building for production...
✓ 2985 modules transformed.
✓ built in 3.62s
```

✅ **No TypeScript errors**
✅ **No ESLint warnings**
✅ **All imports resolved correctly**

## Testing Recommendations

1. **Manual UI Testing:**
   ```bash
   # Start dev server
   nohup ./watch.sh > /tmp/databricks-app-watch.log 2>&1 &

   # Open browser to http://localhost:5173
   # Navigate to Metrics view
   # Select a service
   # Verify histogram metrics show Max/Avg/Min instead of P99/P95/P50/Avg
   ```

2. **Verify API Response:**
   ```bash
   curl -s http://localhost:8000/api/metrics/<service-name>/kpis?time_range=1h | jq '.metrics_by_type.histogram'
   ```

3. **Check Chart Rendering:**
   - Histogram charts should display 3 lines (Max/Avg/Min)
   - Colors should be Red/Blue/Green respectively
   - Time series data should render without errors

## Backwards Compatibility

⚠️ **Breaking Change:** The API response format has changed from `percentiles` to `statistics`

**Impact:**
- Old frontend versions will break with new backend
- Old API clients expecting `percentiles` will receive errors
- Migration is required - no backwards compatibility

**Mitigation:**
- Deploy backend and frontend updates together
- Monitor for API errors after deployment
- Update any external consumers of the KPI endpoint

## Known Limitations

### Why Statistics Instead of Percentiles?

The `metrics_1min_synced` table contains **pre-aggregated** metrics with only:
- `avg_value` - Average across the time window
- `min_value` - Minimum value in the window
- `max_value` - Maximum value in the window
- `sum_value` - Sum of all values

**True percentiles (P50, P95, P99) require raw data points** to calculate accurately. With only aggregated averages, mins, and maxes, we cannot reconstruct percentiles.

### Future Enhancement Path

To restore percentile support:
1. Modify upstream aggregation pipeline
2. Add `p50_value`, `p95_value`, `p99_value` columns to `metrics_1min_synced`
3. Calculate percentiles during aggregation (not after)
4. Update backend queries to use new columns
5. Revert frontend to use `percentiles` structure

## Related Documentation

- Backend changes: `claudedocs/METRICS_SCHEMA_ANALYSIS.md`
- Fix summary: `claudedocs/METRICS_SCHEMA_FIX_SUMMARY.md`
- Architecture: `claudedocs/ARCHITECTURE.md`

## Deployment Checklist

- [x] Backend queries updated
- [x] Frontend types updated
- [x] Frontend components updated
- [x] Frontend builds successfully
- [ ] Integration testing with real data
- [ ] Deploy backend changes
- [ ] Deploy frontend changes
- [ ] Verify metrics display correctly in production
- [ ] Monitor error logs for issues
