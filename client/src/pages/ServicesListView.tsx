import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { ServiceHealth } from '../types/observability';
import { useServiceContext } from '../contexts/ServiceContext';
import { useTimeRange } from '../contexts/TimeRangeContext';

type SortField = 'service_name' | 'health_status' | 'current_latency_p50' | 'current_latency_p95' | 'current_latency_p99' | 'error_rate' | 'request_count' | 'requests_per_second';
type SortOrder = 'asc' | 'desc';

export function ServicesListView() {
  const { timeRange } = useTimeRange();
  const { setSelectedService } = useServiceContext();
  const [sortField, setSortField] = useState<SortField>('request_count');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

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

  const sortedServices = useMemo(() => {
    if (!services) return [];
    
    const sorted = [...services].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = (bVal as string).toLowerCase();
      }
      
      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
    
    return sorted;
  }, [services, sortField, sortOrder]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-4 w-4 opacity-50" />;
    }
    return sortOrder === 'asc' ? 
      <ArrowUp className="h-4 w-4" /> : 
      <ArrowDown className="h-4 w-4" />;
  };

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
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-foreground">Services List</h2>
        <p className="text-sm text-muted-foreground">
          All services with performance metrics
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

      {services && (
        <div className="rounded-lg border border-border bg-card">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th 
                    className="px-4 py-3 text-left text-sm font-semibold text-foreground cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => handleSort('service_name')}
                  >
                    <div className="flex items-center gap-2">
                      Service
                      {getSortIcon('service_name')}
                    </div>
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-sm font-semibold text-foreground cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => handleSort('health_status')}
                  >
                    <div className="flex items-center gap-2">
                      Status
                      {getSortIcon('health_status')}
                    </div>
                  </th>
                  <th 
                    className="px-4 py-3 text-right text-sm font-semibold text-foreground cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => handleSort('current_latency_p50')}
                  >
                    <div className="flex items-center justify-end gap-2">
                      P50 Latency
                      {getSortIcon('current_latency_p50')}
                    </div>
                  </th>
                  <th 
                    className="px-4 py-3 text-right text-sm font-semibold text-foreground cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => handleSort('current_latency_p95')}
                  >
                    <div className="flex items-center justify-end gap-2">
                      P95 Latency
                      {getSortIcon('current_latency_p95')}
                    </div>
                  </th>
                  <th 
                    className="px-4 py-3 text-right text-sm font-semibold text-foreground cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => handleSort('current_latency_p99')}
                  >
                    <div className="flex items-center justify-end gap-2">
                      P99 Latency
                      {getSortIcon('current_latency_p99')}
                    </div>
                  </th>
                  <th 
                    className="px-4 py-3 text-right text-sm font-semibold text-foreground cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => handleSort('error_rate')}
                  >
                    <div className="flex items-center justify-end gap-2">
                      Error Rate
                      {getSortIcon('error_rate')}
                    </div>
                  </th>
                  <th 
                    className="px-4 py-3 text-right text-sm font-semibold text-foreground cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => handleSort('request_count')}
                  >
                    <div className="flex items-center justify-end gap-2">
                      Requests
                      {getSortIcon('request_count')}
                    </div>
                  </th>
                  <th 
                    className="px-4 py-3 text-right text-sm font-semibold text-foreground cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => handleSort('requests_per_second')}
                  >
                    <div className="flex items-center justify-end gap-2">
                      RPS
                      {getSortIcon('requests_per_second')}
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedServices.map((service) => (
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
