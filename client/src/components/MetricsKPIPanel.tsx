import { useQuery } from '@tanstack/react-query';
import { useServiceContext } from '../contexts/ServiceContext';
import { useTimeRange } from '../contexts/TimeRangeContext';
import { ServiceKPIs } from '../types/metrics';
import { HistogramCard, GaugeCard, SumCard } from './MetricCards';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { ServiceHealth } from '../types/observability';

export function MetricsKPIPanel() {
  const { selectedService, setSelectedService } = useServiceContext();
  const { timeRange } = useTimeRange();

  // Fetch available services for the dropdown
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
        {
          credentials: 'include',
        }
      );
      if (!response.ok) throw new Error('Failed to fetch KPIs');
      return response.json();
    },
    enabled: !!selectedService,
  });

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-foreground">Metrics KPIs</h3>
        <p className="text-sm text-muted-foreground">
          Monitor key performance indicators per service
        </p>
      </div>

      {/* Service Selector */}
      <Select value={selectedService || ''} onValueChange={setSelectedService}>
        <SelectTrigger className="w-full">
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

      {/* Loading State */}
      {isLoading && selectedService && (
        <div className="text-sm text-muted-foreground">Loading metrics...</div>
      )}

      {/* Error State */}
      {error && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-3">
          <div className="text-sm text-destructive">{error.message}</div>
        </div>
      )}

      {/* No Service Selected */}
      {!selectedService && !isLoading && (
        <div className="rounded-lg border border-border bg-card p-4 text-center">
          <div className="text-sm text-muted-foreground">
            Select a service to view metrics
          </div>
        </div>
      )}

      {/* No Metrics Found */}
      {kpis?.message && (
        <div className="rounded-lg border border-border bg-card p-4 text-center">
          <div className="text-sm text-muted-foreground">{kpis.message}</div>
        </div>
      )}

      {/* Metrics Display */}
      {kpis && !kpis.message && (
        <div className="space-y-4">
          {/* Histogram Metrics */}
          {kpis.metrics_by_type.histogram &&
            Object.keys(kpis.metrics_by_type.histogram).length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-muted-foreground">
                  📊 Distribution Metrics
                </h4>
                <div className="space-y-2">
                  {Object.values(kpis.metrics_by_type.histogram).map((metric) => (
                    <HistogramCard key={metric.name} metric={metric} />
                  ))}
                </div>
              </div>
            )}

          {/* Gauge Metrics */}
          {kpis.metrics_by_type.gauge &&
            Object.keys(kpis.metrics_by_type.gauge).length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-muted-foreground">
                  📈 Current Values
                </h4>
                <div className="space-y-2">
                  {Object.values(kpis.metrics_by_type.gauge).map((metric) => (
                    <GaugeCard key={metric.name} metric={metric} />
                  ))}
                </div>
              </div>
            )}

          {/* Sum Metrics */}
          {kpis.metrics_by_type.sum &&
            Object.keys(kpis.metrics_by_type.sum).length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-muted-foreground">
                  ➕ Cumulative Metrics
                </h4>
                <div className="space-y-2">
                  {Object.values(kpis.metrics_by_type.sum).map((metric) => (
                    <SumCard key={metric.name} metric={metric} />
                  ))}
                </div>
              </div>
            )}
        </div>
      )}
    </div>
  );
}
