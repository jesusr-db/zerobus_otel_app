import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ServiceGraph } from '../components/ServiceGraph';
import { TimeRangeSelector } from '../components/TimeRangeSelector';
import { useServiceContext } from '../contexts/ServiceContext';
import { DependencyGraph, TimeRange } from '../types/observability';
import { apiClient } from '../fastapi_client';

export function DependencyMapView() {
  const [timeRange, setTimeRange] = useState<TimeRange>('1h');
  const { setSelectedService } = useServiceContext();

  const { data, isLoading, error } = useQuery<DependencyGraph>({
    queryKey: ['dependencies', timeRange],
    queryFn: async () => {
      const response = await fetch(`/api/dependencies/graph?time_range=${timeRange}`, {
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error('Failed to fetch dependency graph');
      }
      return response.json();
    },
    refetchInterval: 30000,
  });

  const handleNodeClick = (serviceId: string) => {
    setSelectedService(serviceId);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Service Dependency Map</h2>
          <p className="text-sm text-muted-foreground">
            Visualize service relationships and health status
          </p>
        </div>
        <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      </div>

      {isLoading && (
        <div className="flex h-full items-center justify-center">
          <div className="text-muted-foreground">Loading dependency graph...</div>
        </div>
      )}

      {error && (
        <div className="flex h-full items-center justify-center">
          <div className="text-destructive">Failed to load dependency graph</div>
        </div>
      )}

      {data && (
        <div className="flex-1 rounded-lg border border-border bg-card">
          <ServiceGraph data={data} onNodeClick={handleNodeClick} />
        </div>
      )}

      <div className="mt-4 flex gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded-full bg-[hsl(160,60%,45%)]" />
          <span className="text-muted-foreground">Healthy</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded-full bg-[hsl(30,80%,55%)]" />
          <span className="text-muted-foreground">Warning</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded-full bg-[hsl(0,63%,31%)]" />
          <span className="text-muted-foreground">Critical</span>
        </div>
      </div>
    </div>
  );
}
