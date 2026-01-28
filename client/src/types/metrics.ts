export interface TimeSeriesPoint {
  time: string;
  value: number;
}

export interface MetricValue {
  value: number;
  trend: "up" | "down" | "stable";
  timeseries?: TimeSeriesPoint[];
  unit?: string;
}

export interface HistogramMetric {
  name: string;
  type: "histogram";
  statistics: {
    avg: MetricValue;
    min: MetricValue;
    max: MetricValue;
  };
}

export interface GaugeMetric {
  name: string;
  type: "gauge";
  gauge: {
    current: MetricValue;
  };
}

export interface SumMetric {
  name: string;
  type: "sum";
  sum: {
    total: MetricValue;
    rate: MetricValue;
  };
}

export type Metric = HistogramMetric | GaugeMetric | SumMetric;

export interface ServiceKPIs {
  service_name: string;
  time_range: string;
  metrics_by_type: {
    histogram?: Record<string, HistogramMetric>;
    gauge?: Record<string, GaugeMetric>;
    sum?: Record<string, SumMetric>;
  };
  message?: string;
}
