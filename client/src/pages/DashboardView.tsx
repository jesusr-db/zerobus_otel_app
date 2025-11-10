import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { ServiceHealth } from '../types/observability';
import { useServiceContext } from '../contexts/ServiceContext';
import { useTimeRange } from '../contexts/TimeRangeContext';

export function DashboardView() {
  const { timeRange } = useTimeRange();
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
  });

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'critical': return 'bg-destructive text-destructive-foreground';
      case 'warning': return 'bg-[hsl(30,80%,55%)] text-primary-foreground';
      case 'healthy': return 'bg-[hsl(160,60%,45%)] text-primary-foreground';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  const handleServiceClick = (serviceName: string) => {
    setSelectedService(serviceName);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-foreground">Service Health Dashboard</h2>
        <p className="text-sm text-muted-foreground">
          Monitor service health and performance metrics
        </p>
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

      {services && services.length === 0 && !isLoading && (
        <div className="flex h-full items-center justify-center">
          <div className="max-w-2xl rounded-lg border border-border bg-card p-6 text-center">
            <div className="text-foreground font-semibold mb-2">No recent data</div>
            <div className="text-sm text-muted-foreground">
              No service activity found in the selected time range. Try selecting a longer time range.
            </div>
          </div>
        </div>
      )}

      {services && services.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {services.map((service) => (
            <Card
              key={service.service_name}
              className="cursor-pointer transition-all hover:border-primary"
              onClick={() => handleServiceClick(service.service_name)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg font-semibold">
                    {service.service_name}
                  </CardTitle>
                  <span className={`rounded-full px-2 py-1 text-xs font-medium ${getHealthColor(service.health_status)}`}>
                    {service.health_status}
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Latency P95:</span>
                    <span className="font-medium">{service.current_latency_p95.toFixed(2)}ms</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Error Rate:</span>
                    <span className="font-medium">{(service.error_rate * 100).toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Requests:</span>
                    <span className="font-medium">{service.request_count.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">RPS:</span>
                    <span className="font-medium">{service.requests_per_second.toFixed(2)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
