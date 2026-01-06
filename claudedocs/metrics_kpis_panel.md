# Metrics KPIs Panel Feature

## Status: ✅ DEPLOYED

**Deployment**: 01f0eb35985617eb88b2923fd218894c
**App State**: ACTIVE
**Deployment Status**: SUCCEEDED
**App URL**: https://o11y-jmr-1351565862180944.aws.databricksapps.com

## Overview

Added a dynamic **Metrics KPIs Panel** on the left side of the Dashboard that discovers and displays service-specific metrics grouped by OpenTelemetry metric type (histogram, gauge, sum).

## Features

### Dynamic Metric Discovery
- **Auto-discovers** all unique metrics per service from `metrics_1min_synced` table
- **Groups by metric type**: histogram, gauge, sum
- **No hardcoded metrics**: Adapts to whatever metrics each service emits
- **Type-aware visualization**: Different display based on metric type

### Service-Based Filtering
- **Single-select dropdown** for service selection
- **Integrated with global time range** picker (5m, 1h, 1d, 1w)
- **Auto-refresh** with React Query (30s intervals)
- Uses existing ServiceContext for state management

### Metric Type Handling

#### 📊 Histogram Metrics (Distribution)
Shows **percentiles** for latency/duration metrics:
- P99 (99th percentile)
- P95 (95th percentile)
- P50 (median)
- Avg (average)

**Display**: Value + trend indicator + sparkline

**Example metrics**:
- `http.server.duration`
- `http.client.duration`
- `database.query.duration`

#### 📈 Gauge Metrics (Current Value)
Shows **current value** for point-in-time measurements:
- Current value with large display
- Trend indicator
- Sparkline visualization
- Color-coded health (green/yellow/red based on value)

**Example metrics**:
- `system.cpu.utilization`
- `system.memory.utilization`
- `jvm.memory.used`
- `connection.pool.active`

#### ➕ Sum Metrics (Cumulative)
Shows **total and rate** for counters:
- Total count
- Rate per second (/s)
- Trend indicators for both
- Sparkline for rate

**Example metrics**:
- `http.server.request.count`
- `http.server.error.count`
- `database.queries.total`

### Visualization Features

#### Sparklines
- **Inline mini-charts** using Recharts
- **Last 10 data points** from time range
- **Color-coded** by metric type
- **Area chart** with gradient fill
- **Size**: 80x20px (compact)

#### Trend Indicators
- **↑ Up**: Increase >5% from baseline
- **↓ Down**: Decrease >5% from baseline
- **→ Stable**: Change <5%

**Color logic**:
- Latency/errors/saturation: Up=🔴, Down=🟢, Stable=⚪
- Throughput/success: Up=🟢, Down=🔴, Stable=⚪

#### Health Color Coding
Uses **existing dashboard color scheme**:
- **Green** (healthy): `hsl(160, 60%, 45%)`
- **Yellow** (warning): `hsl(30, 80%, 55%)`
- **Red** (critical): `hsl(0, 84%, 60%)`

## Architecture

### Backend

**New API Endpoint**: `/api/metrics/{service_name}/kpis`

**Query Parameters**:
- `time_range`: 5m, 1h, 1d, 1w (required)

**Response Structure**:
```json
{
  "service_name": "frontend",
  "time_range": "1h",
  "metrics_by_type": {
    "histogram": {
      "http.server.duration": {
        "name": "http.server.duration",
        "type": "histogram",
        "percentiles": {
          "p50": { "value": 45.2, "trend": "down", "sparkline": [48, 47, 46, ...] },
          "p95": { "value": 98.5, "trend": "stable", "sparkline": [...] },
          "p99": { "value": 125.3, "trend": "up", "sparkline": [...] },
          "avg": { "value": 52.1, "trend": "stable", "sparkline": [...] }
        }
      }
    },
    "gauge": {
      "system.cpu.utilization": {
        "name": "system.cpu.utilization",
        "type": "gauge",
        "gauge": {
          "current": { "value": 45.2, "trend": "stable", "sparkline": [...] }
        }
      }
    },
    "sum": {
      "http.server.request.count": {
        "name": "http.server.request.count",
        "type": "sum",
        "sum": {
          "total": { "value": 4300000, "trend": "up" },
          "rate": { "value": 1234.5, "unit": "/s", "trend": "up", "sparkline": [...] }
        }
      }
    }
  }
}
```

**Query Logic**:
1. Discover unique metrics for service from `metrics_1min_synced`
2. Group by `metric_type` column
3. Query current period (last N hours/days)
4. Query baseline period (previous period for trend calculation)
5. Calculate percentiles, averages, sums, rates
6. Generate sparkline data (last 10 data points)
7. Calculate trends (compare current vs baseline)

### Frontend

**New Components**:

1. **`MetricsKPIPanel.tsx`** - Main panel container
   - Service selector dropdown
   - Metrics grouping by type
   - Loading/error states
   - Auto-refresh with React Query

2. **`MetricCards.tsx`** - Type-specific card components
   - `HistogramCard` - Shows percentiles
   - `GaugeCard` - Shows current value with health color
   - `SumCard` - Shows total and rate

3. **`Sparkline.tsx`** - Mini chart component
   - Uses Recharts AreaChart
   - Gradient fill
   - Configurable color
   - Responsive size

4. **`types/metrics.ts`** - TypeScript types
   - `ServiceKPIs`
   - `HistogramMetric`, `GaugeMetric`, `SumMetric`
   - `MetricValue`

**Layout Changes**:
- Dashboard split into **2-column layout**
- **Left**: 320px fixed-width panel (Metrics KPIs)
- **Right**: Flex-grow panel (Service Health Grid)
- Both panels **independently scrollable**

## Files Created/Modified

### Backend
- **Created**: `server/routers/metrics_kpis.py` - New metrics KPIs endpoint
- **Modified**: `server/app.py` - Added metrics router

### Frontend
- **Created**: `client/src/types/metrics.ts` - Metrics types
- **Created**: `client/src/components/Sparkline.tsx` - Sparkline component
- **Created**: `client/src/components/MetricCards.tsx` - Metric card components
- **Created**: `client/src/components/MetricsKPIPanel.tsx` - Main panel
- **Modified**: `client/src/pages/DashboardView.tsx` - Added panel to layout

## Data Flow

```
User selects service in dropdown
    ↓
React Query fetches: /api/metrics/{service}/kpis?time_range=1h
    ↓
Backend queries metrics_1min_synced:
  1. Find unique metrics for service
  2. Group by metric_type
  3. Calculate current + baseline values
  4. Generate sparklines
  5. Calculate trends
    ↓
Return grouped metrics by type
    ↓
Frontend renders appropriate cards:
  - Histogram → HistogramCard (percentiles)
  - Gauge → GaugeCard (current value)
  - Sum → SumCard (total + rate)
    ↓
Display with sparklines and trend indicators
```

## Usage

### Viewing Metrics KPIs

1. **Open Dashboard**: https://o11y-jmr-1351565862180944.aws.databricksapps.com
2. **Select a service** from the dropdown in the left panel
3. **Metrics auto-load** based on global time range
4. **View metrics grouped by type**:
   - Distribution metrics (histograms)
   - Current values (gauges)
   - Cumulative metrics (sums)

### Understanding Visualizations

**Histogram (Distribution)**:
- Shows how values are distributed
- P99 = 99% of requests faster than this
- P50 = Median (50th percentile)

**Gauge (Current Value)**:
- Current point-in-time measurement
- Color indicates health (green/yellow/red)
- Sparkline shows recent trend

**Sum (Cumulative)**:
- Total count over time period
- Rate shows per-second throughput
- Trend shows if increasing/decreasing

### Interpreting Trends

- **↑ Up + Red**: Bad (latency increasing, errors up)
- **↑ Up + Green**: Good (throughput increasing)
- **↓ Down + Green**: Good (latency decreasing, errors down)
- **↓ Down + Red**: Bad (throughput decreasing)
- **→ Stable**: No significant change

## Example Scenarios

### Scenario 1: Latency Spike Investigation
1. Select service with high latency
2. View histogram metrics → P99 is 🔴↑ (trending up)
3. Check gauge metrics → CPU/memory high
4. Check sum metrics → Request rate 🟢↑ (traffic spike)
**Diagnosis**: High traffic causing resource saturation

### Scenario 2: Error Rate Monitoring
1. Select service
2. View sum metrics → `http.server.error.count` 🔴↑
3. Check histogram → P99 latency normal
4. Check gauge → Resources normal
**Diagnosis**: Application error, not infrastructure

### Scenario 3: Resource Monitoring
1. Select service
2. View gauge metrics:
   - CPU: 78% 🔴↑ (trending up)
   - Memory: 45% 🟢→ (stable)
3. View histogram → Latency 🔴↑ (increasing)
**Diagnosis**: CPU bottleneck affecting latency

## Benefits

### For SREs
- **Quick health check** per service
- **Metric type awareness** (histogram vs gauge vs sum)
- **Trend indicators** show direction
- **Sparklines** show recent patterns
- **No hardcoded metrics** - adapts to each service

### For Development
- **TypeScript types** for safety
- **React Query** for caching and auto-refresh
- **shadcn/ui** for consistent styling
- **Recharts** for visualizations
- **Modular components** for maintainability

### For Observability
- **Dynamic discovery** of metrics
- **OpenTelemetry standard** compliance
- **Real-time updates** from Lakebase
- **Service-specific** KPIs
- **Multi-signal** visibility (traces + logs + metrics)

## Performance

**Query Performance**:
- Metrics query: ~100-300ms
- Uses indexes on `service_name`, `window_start`, `name`
- Sparkline data limited to 10 points
- Auto-refresh every 30 seconds

**Frontend Performance**:
- React Query caching reduces redundant requests
- Sparklines use lightweight Recharts component
- Card-based layout lazy-loads as needed
- Efficient re-renders with React.memo if needed

## Future Enhancements

### Potential Additions
- **Multi-service comparison** (compare 2-3 services side-by-side)
- **Custom metric selection** (choose which metrics to display)
- **Alerts/thresholds** (configurable warning/critical levels)
- **Metric favorites** (pin frequently viewed metrics)
- **Export metrics** (CSV/JSON download)
- **Larger chart view** (click metric to see full-size chart)
- **Correlation detection** (auto-highlight related metrics)

### Technical Improvements
- **Metric metadata** (units, descriptions from OTEL semantic conventions)
- **Aggregation options** (min/max/sum/avg customization)
- **Time comparison** (compare current vs previous week)
- **Anomaly detection** (highlight unusual values)
- **Metric relationships** (show dependencies between metrics)

## Troubleshooting

### No Metrics Showing
**Symptoms**: "No metrics found for this service"

**Causes**:
1. Service has no metrics in time range
2. Service name mismatch
3. No data in `metrics_1min_synced` table

**Solutions**:
- Try longer time range (1h → 1d)
- Verify service name matches exactly
- Check metrics ingestion pipeline

### Sparklines Not Rendering
**Symptoms**: Gray rectangles instead of charts

**Causes**:
1. No sparkline data in response
2. All values are 0 or null
3. Recharts not loaded

**Solutions**:
- Check API response has `sparkline` arrays
- Verify time range has data points
- Check browser console for errors

### Slow Loading
**Symptoms**: Panel takes >2 seconds to load

**Causes**:
1. Large number of metrics for service
2. Complex percentile calculations
3. Network latency

**Solutions**:
- Add database indexes on query columns
- Cache frequently accessed services
- Reduce sparkline data points
- Optimize SQL query with EXPLAIN

## Testing

### Manual Testing Steps

1. **Test different services**:
   - Select each service in dropdown
   - Verify metrics appear

2. **Test different time ranges**:
   - 5m, 1h, 1d, 1w
   - Verify data changes appropriately

3. **Test metric types**:
   - Find service with histograms (latency metrics)
   - Find service with gauges (resource metrics)
   - Find service with sums (request counts)

4. **Test edge cases**:
   - Service with no metrics
   - Service with 1 metric type only
   - Service with many metrics (>10)

5. **Test interactions**:
   - Change service while loading
   - Change time range rapidly
   - Refresh page (state persistence)

### Validation Queries

**Check available metrics**:
```sql
SELECT service_name, metric_type, COUNT(DISTINCT name) as metric_count
FROM zerobus_sdp.metrics_1min_synced
GROUP BY service_name, metric_type
ORDER BY metric_count DESC;
```

**Sample metrics for service**:
```sql
SELECT DISTINCT name, metric_type
FROM zerobus_sdp.metrics_1min_synced
WHERE service_name = 'frontend'
  AND window_start >= NOW() - INTERVAL '1 HOUR'
ORDER BY metric_type, name;
```

## Lessons Learned

1. **Dynamic > Hardcoded**: Discovering metrics per service is more flexible than hardcoding Golden Signals
2. **Type-aware UI**: Different visualizations for histogram vs gauge vs sum provides better UX
3. **Existing color scheme**: Reusing dashboard colors ensures visual consistency
4. **Sparklines**: Inline micro-charts provide context without overwhelming
5. **Service context**: Leveraging existing ServiceContext avoided duplicate state management

## Related Features

This complements the existing observability features:
- **Service Health Dashboard** (right panel) - Overall service status
- **Dependency Map** - Service relationships
- **Traces View** - Individual request traces
- **Real-time Traces** - Uses `traces_silver_synced`
- **Unified OTEL Signals** - Combines traces + logs + metrics

Together, these provide **comprehensive observability** across all OpenTelemetry signal types.
