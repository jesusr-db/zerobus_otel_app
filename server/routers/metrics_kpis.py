from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal, Dict, List, Any
import logging
from server.services.lakebase_manager import LakebaseManager
from server.config import LAKEBASE_SCHEMA_NAME

logger = logging.getLogger(__name__)
router = APIRouter()

TimeRange = Literal["5m", "1h", "1d", "1w"]


def get_time_range_interval(time_range: TimeRange) -> tuple[str, int]:
    """
    Convert time range to SQL interval string and seconds.

    Note: PostgreSQL requires lowercase with plural forms for quantities > 1
    """
    intervals = {
        "5m": ("5 minutes", 300),
        "1h": ("1 hour", 3600),
        "1d": ("1 day", 86400),
        "1w": ("7 days", 604800),
    }
    return intervals[time_range]


def get_bucket_size(time_range: TimeRange) -> tuple[str, int]:
    """
    Get appropriate bucket size for aggregation based on time range.
    Returns (interval_string, bucket_size_in_seconds).

    Note: Use bucket_seconds with epoch-based bucketing for custom intervals:
    to_timestamp(floor(extract(epoch from timestamp) / bucket_seconds) * bucket_seconds)

    Bucketing strategy:
    - 5m: 1 minute buckets (5 data points)
    - 1h: 5 minute buckets (12 data points)
    - 1d: 1 hour buckets (24 data points)
    - 1w: 4 hour buckets (42 data points)
    """
    buckets = {
        "5m": ("1 minute", 60),       # 5 buckets
        "1h": ("5 minutes", 300),     # 12 buckets (use epoch bucketing)
        "1d": ("1 hour", 3600),       # 24 buckets
        "1w": ("4 hours", 14400),     # 42 buckets (use epoch bucketing)
    }
    return buckets[time_range]


def calculate_trend(current: float, baseline: float) -> str:
    """Calculate trend direction based on current vs baseline."""
    if baseline == 0:
        return "stable"

    change_percent = ((current - baseline) / baseline) * 100

    if change_percent > 5:
        return "up"
    elif change_percent < -5:
        return "down"
    else:
        return "stable"


@router.get("/{service_name}/kpis")
async def get_service_kpis(
    request: Request,
    service_name: str,
    time_range: TimeRange = Query(default="1h", description="Time range for metrics")
):
    """
    Get KPI metrics for a specific service, dynamically discovering available metrics
    and grouping them by type (histogram, gauge, sum).
    """
    user_token = request.headers.get("X-Forwarded-Access-Token")
    lakebase = LakebaseManager(user_token=user_token)
    interval, seconds = get_time_range_interval(time_range)
    bucket_interval, bucket_seconds = get_bucket_size(time_range)

    try:
        # Query to get unique metrics for this service grouped by type
        metrics_discovery_query = f"""
        SELECT DISTINCT
            name,
            metric_type
        FROM {LAKEBASE_SCHEMA_NAME}.metrics_1min_synced
        WHERE service_name = '{service_name}'
            AND window_start >= NOW() - INTERVAL '{interval}'
        ORDER BY metric_type, name
        """

        available_metrics = lakebase.execute_query(metrics_discovery_query)

        if not available_metrics:
            return {
                "service_name": service_name,
                "time_range": time_range,
                "metrics": {},
                "message": "No metrics found for this service in the selected time range"
            }

        # Group metrics by type
        metrics_by_type: Dict[str, List[str]] = {}
        for metric in available_metrics:
            metric_type = metric['metric_type'] or 'unknown'
            metric_name = metric['name']
            if metric_type not in metrics_by_type:
                metrics_by_type[metric_type] = []
            metrics_by_type[metric_type].append(metric_name)

        # Query current and baseline data for each metric
        result = {
            "service_name": service_name,
            "time_range": time_range,
            "metrics_by_type": {}
        }

        for metric_type, metric_names in metrics_by_type.items():
            result["metrics_by_type"][metric_type] = {}

            for metric_name in metric_names:
                # Current period query with time-based bucketing for efficient aggregation
                # Using epoch-based bucketing for custom intervals (PostgreSQL DATE_TRUNC only accepts single precision)
                # Note: Schema only has avg/min/max/sum - no percentile columns available
                current_query = f"""
                WITH bucketed_data AS (
                    SELECT
                        to_timestamp(floor(extract(epoch from window_start) / {bucket_seconds}) * {bucket_seconds}) as bucket_time,
                        AVG(avg_value) as bucket_avg,
                        AVG(min_value) as bucket_min,
                        AVG(max_value) as bucket_max,
                        SUM(sum_value) as bucket_sum,
                        SUM(sample_count) as bucket_samples
                    FROM {LAKEBASE_SCHEMA_NAME}.metrics_1min_synced
                    WHERE service_name = '{service_name}'
                        AND name = '{metric_name}'
                        AND window_start >= NOW() - INTERVAL '{interval}'
                    GROUP BY bucket_time
                    ORDER BY bucket_time ASC
                )
                SELECT
                    AVG(bucket_avg) as avg_avg,
                    AVG(bucket_min) as avg_min,
                    AVG(bucket_max) as avg_max,
                    SUM(bucket_sum) as total_sum,
                    SUM(bucket_samples) as total_samples,
                    array_agg(bucket_time ORDER BY bucket_time ASC) as timestamps,
                    array_agg(bucket_avg ORDER BY bucket_time ASC) as sparkline_avg,
                    array_agg(bucket_min ORDER BY bucket_time ASC) as sparkline_min,
                    array_agg(bucket_max ORDER BY bucket_time ASC) as sparkline_max,
                    array_agg(bucket_sum ORDER BY bucket_time ASC) as sparkline_sum
                FROM bucketed_data
                """

                current_data = lakebase.execute_query(current_query)

                # Baseline period query (previous period for trend calculation)
                # Using epoch-based bucketing for custom intervals
                # Note: Schema only has avg/min/max/sum - no percentile columns available
                baseline_query = f"""
                WITH bucketed_baseline AS (
                    SELECT
                        to_timestamp(floor(extract(epoch from window_start) / {bucket_seconds}) * {bucket_seconds}) as bucket_time,
                        AVG(avg_value) as bucket_avg,
                        AVG(min_value) as bucket_min,
                        AVG(max_value) as bucket_max,
                        SUM(sum_value) as bucket_sum
                    FROM {LAKEBASE_SCHEMA_NAME}.metrics_1min_synced
                    WHERE service_name = '{service_name}'
                        AND name = '{metric_name}'
                        AND window_start >= NOW() - INTERVAL '{interval}' * 2
                        AND window_start < NOW() - INTERVAL '{interval}'
                    GROUP BY bucket_time
                )
                SELECT
                    AVG(bucket_avg) as baseline_avg,
                    AVG(bucket_min) as baseline_min,
                    AVG(bucket_max) as baseline_max,
                    SUM(bucket_sum) as baseline_sum
                FROM bucketed_baseline
                """

                baseline_data = lakebase.execute_query(baseline_query)

                if not current_data or not current_data[0]:
                    continue

                current = current_data[0]
                baseline = baseline_data[0] if baseline_data and baseline_data[0] else {}

                # Helper function to create time series data
                def create_time_series(timestamps, values):
                    """Create array of {time, value} objects for charts."""
                    if not timestamps or not values:
                        return []
                    return [
                        {"time": str(ts), "value": round(val or 0, 2)}
                        for ts, val in zip(timestamps, values)
                    ]

                timestamps = current.get('timestamps', [])

                # Build metric data based on type
                metric_data: Dict[str, Any] = {
                    "name": metric_name,
                    "type": metric_type
                }

                if metric_type == "histogram":
                    # Histogram: Show statistics with time series data
                    # Note: Percentiles not available in aggregated schema - showing avg/min/max instead
                    metric_data["statistics"] = {
                        "avg": {
                            "value": round(current['avg_avg'] or 0, 2),
                            "trend": calculate_trend(
                                current['avg_avg'] or 0,
                                baseline.get('baseline_avg') or current['avg_avg'] or 0
                            ),
                            "timeseries": create_time_series(timestamps, current.get('sparkline_avg', []))
                        },
                        "min": {
                            "value": round(current['avg_min'] or 0, 2),
                            "trend": calculate_trend(
                                current['avg_min'] or 0,
                                baseline.get('baseline_min') or current['avg_min'] or 0
                            ),
                            "timeseries": create_time_series(timestamps, current.get('sparkline_min', []))
                        },
                        "max": {
                            "value": round(current['avg_max'] or 0, 2),
                            "trend": calculate_trend(
                                current['avg_max'] or 0,
                                baseline.get('baseline_max') or current['avg_max'] or 0
                            ),
                            "timeseries": create_time_series(timestamps, current.get('sparkline_max', []))
                        }
                    }

                elif metric_type == "gauge":
                    # Gauge: Show current value with time series
                    metric_data["gauge"] = {
                        "current": {
                            "value": round(current['avg_avg'] or 0, 2),
                            "trend": calculate_trend(
                                current['avg_avg'] or 0,
                                baseline.get('baseline_avg') or current['avg_avg'] or 0
                            ),
                            "timeseries": create_time_series(timestamps, current.get('sparkline_avg', []))
                        }
                    }

                elif metric_type == "sum":
                    # Sum: Show total and rate with time series
                    total_sum = current['total_sum'] or 0
                    rate = total_sum / seconds if seconds > 0 else 0
                    baseline_sum = baseline.get('baseline_sum') or total_sum
                    baseline_rate = baseline_sum / seconds if seconds > 0 else 0

                    metric_data["sum"] = {
                        "total": {
                            "value": round(total_sum, 2),
                            "trend": calculate_trend(total_sum, baseline_sum)
                        },
                        "rate": {
                            "value": round(rate, 2),
                            "unit": "/s",
                            "trend": calculate_trend(rate, baseline_rate),
                            "timeseries": create_time_series(timestamps, current.get('sparkline_sum', []))
                        }
                    }

                result["metrics_by_type"][metric_type][metric_name] = metric_data

        return result

    except Exception as e:
        logger.error(f"KPIs query failed for {service_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
