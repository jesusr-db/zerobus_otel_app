from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal, Dict, List, Any
import logging
from server.services.lakebase_manager import LakebaseManager
from server.config import DATA_BACKEND

logger = logging.getLogger(__name__)
router = APIRouter()

TimeRange = Literal["5m", "1h", "1d", "1w"]


def get_time_range_interval(time_range: TimeRange) -> tuple[str, int]:
    """Convert time range to SQL interval string and seconds."""
    intervals = {
        "5m": ("5 MINUTE", 300),
        "1h": ("1 HOUR", 3600),
        "1d": ("1 DAY", 86400),
        "1w": ("7 DAY", 604800),
    }
    return intervals[time_range]


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

    if DATA_BACKEND != "lakebase":
        raise HTTPException(status_code=501, detail="Metrics KPIs only supported with Lakebase backend")

    lakebase = LakebaseManager(user_token=user_token)
    interval, seconds = get_time_range_interval(time_range)

    try:
        # Query to get unique metrics for this service grouped by type
        metrics_discovery_query = f"""
        SELECT DISTINCT
            name,
            metric_type
        FROM zerobus_sdp.metrics_1min_synced
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
                # Current period query with timestamps
                current_query = f"""
                WITH recent_data AS (
                    SELECT
                        window_start,
                        avg_value,
                        p50_value,
                        p95_value,
                        p99_value,
                        sum_value,
                        sample_count
                    FROM zerobus_sdp.metrics_1min_synced
                    WHERE service_name = '{service_name}'
                        AND name = '{metric_name}'
                        AND window_start >= NOW() - INTERVAL '{interval}'
                    ORDER BY window_start ASC
                    LIMIT 60
                )
                SELECT
                    AVG(avg_value) as avg_avg,
                    AVG(p50_value) as avg_p50,
                    AVG(p95_value) as avg_p95,
                    AVG(p99_value) as avg_p99,
                    SUM(sum_value) as total_sum,
                    SUM(sample_count) as total_samples,
                    array_agg(window_start ORDER BY window_start ASC) as timestamps,
                    array_agg(avg_value ORDER BY window_start ASC) as sparkline_avg,
                    array_agg(p50_value ORDER BY window_start ASC) as sparkline_p50,
                    array_agg(p95_value ORDER BY window_start ASC) as sparkline_p95,
                    array_agg(p99_value ORDER BY window_start ASC) as sparkline_p99,
                    array_agg(sum_value ORDER BY window_start ASC) as sparkline_sum
                FROM recent_data
                """

                current_data = lakebase.execute_query(current_query)

                # Baseline period query (previous period for trend calculation)
                baseline_query = f"""
                SELECT
                    AVG(avg_value) as baseline_avg,
                    AVG(p50_value) as baseline_p50,
                    AVG(p95_value) as baseline_p95,
                    AVG(p99_value) as baseline_p99,
                    SUM(sum_value) as baseline_sum
                FROM zerobus_sdp.metrics_1min_synced
                WHERE service_name = '{service_name}'
                    AND name = '{metric_name}'
                    AND window_start >= NOW() - INTERVAL '{interval}' * 2
                    AND window_start < NOW() - INTERVAL '{interval}'
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
                    # Histogram: Show percentiles with time series data
                    metric_data["percentiles"] = {
                        "p50": {
                            "value": round(current['avg_p50'] or 0, 2),
                            "trend": calculate_trend(
                                current['avg_p50'] or 0,
                                baseline.get('baseline_p50') or current['avg_p50'] or 0
                            ),
                            "timeseries": create_time_series(timestamps, current.get('sparkline_p50', []))
                        },
                        "p95": {
                            "value": round(current['avg_p95'] or 0, 2),
                            "trend": calculate_trend(
                                current['avg_p95'] or 0,
                                baseline.get('baseline_p95') or current['avg_p95'] or 0
                            ),
                            "timeseries": create_time_series(timestamps, current.get('sparkline_p95', []))
                        },
                        "p99": {
                            "value": round(current['avg_p99'] or 0, 2),
                            "trend": calculate_trend(
                                current['avg_p99'] or 0,
                                baseline.get('baseline_p99') or current['avg_p99'] or 0
                            ),
                            "timeseries": create_time_series(timestamps, current.get('sparkline_p99', []))
                        },
                        "avg": {
                            "value": round(current['avg_avg'] or 0, 2),
                            "trend": calculate_trend(
                                current['avg_avg'] or 0,
                                baseline.get('baseline_avg') or current['avg_avg'] or 0
                            ),
                            "timeseries": create_time_series(timestamps, current.get('sparkline_avg', []))
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
