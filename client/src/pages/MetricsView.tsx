import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTimeRange } from '../contexts/TimeRangeContext';
import { ServiceKPIs } from '../types/metrics';
import { ServiceHealth } from '../types/observability';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { MetricMultiLineChart } from '../components/MetricMultiLineChart';
import { MetricGauge } from '../components/MetricGauge';
import { MetricBarChart } from '../components/MetricBarChart';
import { ArrowUp, ArrowDown, Minus, Search } from 'lucide-react';

interface TrendIconProps {
  trend: 'up' | 'down' | 'stable';
  inverted?: boolean;
}

function TrendIcon({ trend, inverted = false }: TrendIconProps) {
  const getColor = () => {
    if (trend === 'stable') return 'text-muted-foreground';
    const isPositive = inverted ? trend === 'down' : trend === 'up';
    return isPositive ? 'text-[hsl(160,60%,45%)]' : 'text-destructive';
  };

  const Icon = trend === 'up' ? ArrowUp : trend === 'down' ? ArrowDown : Minus;
  return <Icon className={`h-4 w-4 ${getColor()}`} />;
}

export function MetricsView() {
  const { timeRange } = useTimeRange();
  const [selectedService, setSelectedService] = useState<string>('');
  const [searchFilter, setSearchFilter] = useState<string>('');

  // Fetch available services
  const { data: services } = useQuery<ServiceHealth[]>({
    queryKey: ['services', timeRange],
    queryFn: async () => {
      const response = await fetch(`/api/services/list?time_range=${timeRange}`, {
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to fetch services');
      return response.json();
    },
  });

  // Fetch metrics KPIs for selected service
  const { data: kpis, isLoading, error } = useQuery<ServiceKPIs>({
    queryKey: ['service-kpis', selectedService, timeRange],
    queryFn: async () => {
      if (!selectedService) throw new Error('No service selected');
      const response = await fetch(
        `/api/metrics/${selectedService}/kpis?time_range=${timeRange}`,
        { credentials: 'include' }
      );
      if (!response.ok) throw new Error('Failed to fetch KPIs');
      return response.json();
    },
    enabled: !!selectedService,
  });

  // Filter metrics by search term
  const filterMetrics = (metricName: string) => {
    if (!searchFilter) return true;
    return metricName.toLowerCase().includes(searchFilter.toLowerCase());
  };

  // Get all metrics flattened and filtered
  const getAllMetrics = () => {
    if (!kpis || !kpis.metrics_by_type) return [];

    const metrics: Array<{
      name: string;
      type: string;
      data: any;
    }> = [];

    // Add histogram metrics
    if (kpis.metrics_by_type.histogram) {
      Object.entries(kpis.metrics_by_type.histogram).forEach(([name, metric]) => {
        if (filterMetrics(name)) {
          metrics.push({ name, type: 'histogram', data: metric });
        }
      });
    }

    // Add gauge metrics
    if (kpis.metrics_by_type.gauge) {
      Object.entries(kpis.metrics_by_type.gauge).forEach(([name, metric]) => {
        if (filterMetrics(name)) {
          metrics.push({ name, type: 'gauge', data: metric });
        }
      });
    }

    // Add sum metrics
    if (kpis.metrics_by_type.sum) {
      Object.entries(kpis.metrics_by_type.sum).forEach(([name, metric]) => {
        if (filterMetrics(name)) {
          metrics.push({ name, type: 'sum', data: metric });
        }
      });
    }

    return metrics;
  };

  const allMetrics = getAllMetrics();

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-foreground">Metrics</h2>
        <p className="text-sm text-muted-foreground">
          Monitor service metrics and key performance indicators
        </p>
      </div>

      {/* Filter Bar */}
      <div className="mb-6 flex gap-4">
        <Select value={selectedService} onValueChange={setSelectedService}>
          <SelectTrigger className="w-80">
            <SelectValue placeholder="Select a service" />
          </SelectTrigger>
          <SelectContent>
            {services?.map((service) => (
              <SelectItem key={service.service_name} value={service.service_name}>
                {service.service_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search metrics..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="pl-10"
            disabled={!selectedService}
          />
        </div>
      </div>

      {/* Loading State */}
      {isLoading && selectedService && (
        <div className="flex h-full items-center justify-center">
          <div className="text-muted-foreground">Loading metrics...</div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="flex h-full items-center justify-center">
          <div className="max-w-2xl rounded-lg border border-destructive bg-destructive/10 p-4">
            <div className="text-destructive font-semibold mb-2">Failed to load metrics</div>
            <div className="text-sm text-muted-foreground">{error.message}</div>
          </div>
        </div>
      )}

      {/* No Service Selected */}
      {!selectedService && !isLoading && (
        <div className="flex h-full items-center justify-center">
          <div className="max-w-2xl rounded-lg border border-border bg-card p-6 text-center">
            <div className="text-foreground font-semibold mb-2">No service selected</div>
            <div className="text-sm text-muted-foreground">
              Select a service from the dropdown above to view its metrics
            </div>
          </div>
        </div>
      )}

      {/* No Metrics Found */}
      {kpis?.message && (
        <div className="flex h-full items-center justify-center">
          <div className="max-w-2xl rounded-lg border border-border bg-card p-6 text-center">
            <div className="text-foreground font-semibold mb-2">No metrics available</div>
            <div className="text-sm text-muted-foreground">{kpis.message}</div>
          </div>
        </div>
      )}

      {/* No Search Results */}
      {selectedService && !isLoading && !error && !kpis?.message && allMetrics.length === 0 && searchFilter && (
        <div className="flex h-full items-center justify-center">
          <div className="max-w-2xl rounded-lg border border-border bg-card p-6 text-center">
            <div className="text-foreground font-semibold mb-2">No metrics match your search</div>
            <div className="text-sm text-muted-foreground">
              Try a different search term or clear the filter
            </div>
          </div>
        </div>
      )}

      {/* Metrics Display */}
      {selectedService && !isLoading && !error && !kpis?.message && allMetrics.length > 0 && (
        <div className="space-y-4 overflow-y-auto">
          {allMetrics.map((metric) => (
            <Card key={metric.name}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg font-semibold">
                    {metric.type === 'histogram' && '📊 '}
                    {metric.type === 'gauge' && '📈 '}
                    {metric.type === 'sum' && '➕ '}
                    {metric.name}
                  </CardTitle>
                  <span className="text-xs text-muted-foreground uppercase">
                    {metric.type}
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                {/* Histogram Display */}
                {metric.type === 'histogram' && (
                  <div className="space-y-4">
                    {/* Current Values Summary */}
                    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                      <div className="space-y-1">
                        <span className="text-xs text-muted-foreground">P99</span>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold">{metric.data.percentiles.p99.value}</span>
                          <TrendIcon trend={metric.data.percentiles.p99.trend} />
                        </div>
                      </div>
                      <div className="space-y-1">
                        <span className="text-xs text-muted-foreground">P95</span>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold">{metric.data.percentiles.p95.value}</span>
                          <TrendIcon trend={metric.data.percentiles.p95.trend} />
                        </div>
                      </div>
                      <div className="space-y-1">
                        <span className="text-xs text-muted-foreground">P50</span>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold">{metric.data.percentiles.p50.value}</span>
                          <TrendIcon trend={metric.data.percentiles.p50.trend} />
                        </div>
                      </div>
                      <div className="space-y-1">
                        <span className="text-xs text-muted-foreground">Avg</span>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold">{metric.data.percentiles.avg.value}</span>
                          <TrendIcon trend={metric.data.percentiles.avg.trend} />
                        </div>
                      </div>
                    </div>

                    {/* Combined Percentile Chart */}
                    <div className="mt-4">
                      <MetricMultiLineChart
                        series={[
                          {
                            name: 'P99',
                            data: metric.data.percentiles.p99.timeseries || [],
                            color: 'hsl(280, 70%, 60%)'
                          },
                          {
                            name: 'P95',
                            data: metric.data.percentiles.p95.timeseries || [],
                            color: 'hsl(200, 70%, 55%)'
                          },
                          {
                            name: 'P50',
                            data: metric.data.percentiles.p50.timeseries || [],
                            color: 'hsl(160, 60%, 45%)'
                          },
                          {
                            name: 'Avg',
                            data: metric.data.percentiles.avg.timeseries || [],
                            color: 'hsl(220, 70%, 60%)'
                          }
                        ]}
                        height={280}
                      />
                    </div>
                  </div>
                )}

                {/* Gauge Display */}
                {metric.type === 'gauge' && (
                  <div className="py-4">
                    <MetricGauge
                      value={metric.data.gauge.current.value}
                      unit={metric.data.gauge.current.unit}
                      timeseries={metric.data.gauge.current.timeseries}
                    />
                  </div>
                )}

                {/* Sum Display */}
                {metric.type === 'sum' && (
                  <div className="space-y-4">
                    {/* Total Count */}
                    <div className="flex items-center justify-between p-4 bg-muted/20 rounded-lg">
                      <span className="text-sm font-medium text-muted-foreground">Total Count</span>
                      <div className="flex items-center gap-2">
                        <span className="text-2xl font-bold">{metric.data.sum.total.value.toLocaleString()}</span>
                        <TrendIcon trend={metric.data.sum.total.trend} />
                      </div>
                    </div>

                    {/* Rate with Bar Chart */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-muted-foreground">Rate per Second</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xl font-bold">
                            {metric.data.sum.rate.value}{metric.data.sum.rate.unit}
                          </span>
                          <TrendIcon trend={metric.data.sum.rate.trend} />
                        </div>
                      </div>
                      {metric.data.sum.rate.timeseries && metric.data.sum.rate.timeseries.length > 0 && (
                        <MetricBarChart
                          data={metric.data.sum.rate.timeseries}
                          color="hsl(260, 70%, 55%)"
                          height={180}
                        />
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
