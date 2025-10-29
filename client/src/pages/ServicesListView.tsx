import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TimeRangeSelector } from '../components/TimeRangeSelector';
import { ServiceHealth, TimeRange } from '../types/observability';
import { useServiceContext } from '../contexts/ServiceContext';

export function ServicesListView() {
  const [timeRange, setTimeRange] = useState<TimeRange>('1h');
  const { setSelectedService } = useServiceContext();

  const { data: services, isLoading, error } = useQuery<ServiceHealth[]>({
    queryKey: ['services', timeRange],
    queryFn: async () => {
      const response = await fetch(`/api/services/list?time_range=${timeRange}`, {
        credentials: 'include',
      });
      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error:', response.status, errorText);
        throw new Error(`Failed to fetch services: ${response.status} - ${errorText}`);
      }
      return response.json();
    },
    refetchInterval: 30000,
  });

  const getHealthBadge = (status: string) => {
    const colors = {
      critical: 'bg-destructive text-destructive-foreground',
      warning: 'bg-[hsl(30,80%,55%)] text-primary-foreground',
      healthy: 'bg-[hsl(160,60%,45%)] text-primary-foreground',
    };
    return colors[status as keyof typeof colors] || 'bg-muted text-muted-foreground';
  };

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Services List</h2>
          <p className="text-sm text-muted-foreground">
            All services with performance metrics
          </p>
        </div>
        <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      </div>

      {isLoading && (
        <div className="flex h-full items-center justify-center">
          <div className="text-muted-foreground">Loading services...</div>
        </div>
      )}

      {error && (
        <div className="flex h-full items-center justify-center">
          <div className="max-w-2xl rounded-lg border border-destructive bg-destructive/10 p-4">
            <div className="text-destructive font-semibold mb-2">Failed to load services</div>
            <div className="text-sm text-muted-foreground">{error.message}</div>
          </div>
        </div>
      )}

      {services && (
        <div className="rounded-lg border border-border bg-card">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-foreground">Service</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-foreground">Status</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-foreground">P50 Latency</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-foreground">P95 Latency</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-foreground">P99 Latency</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-foreground">Error Rate</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-foreground">Requests</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-foreground">RPS</th>
                </tr>
              </thead>
              <tbody>
                {services.map((service) => (
                  <tr
                    key={service.service_name}
                    className="border-b border-border hover:bg-accent/50 cursor-pointer transition-colors"
                    onClick={() => setSelectedService(service.service_name)}
                  >
                    <td className="px-4 py-3 text-sm font-medium text-foreground">
                      {service.service_name}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getHealthBadge(service.health_status)}`}>
                        {service.health_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-muted-foreground">
                      {service.current_latency_p50.toFixed(2)}ms
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-muted-foreground">
                      {service.current_latency_p95.toFixed(2)}ms
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-muted-foreground">
                      {service.current_latency_p99.toFixed(2)}ms
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-muted-foreground">
                      {(service.error_rate * 100).toFixed(2)}%
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-muted-foreground">
                      {service.request_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-muted-foreground">
                      {service.requests_per_second.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
