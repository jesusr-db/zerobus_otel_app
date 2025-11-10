import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTimeRange } from '../contexts/TimeRangeContext';

interface TraceInfo {
  trace_id: string;
  trace_start: string;
  services_involved: string[];
  total_duration_ms: number;
  span_count: number;
}

interface TracesViewProps {
  onTraceClick: (traceId: string) => void;
}

export function TracesView({ onTraceClick }: TracesViewProps) {
  const { timeRange } = useTimeRange();
  const [selectedService, setSelectedService] = useState<string>('');

  const { data: allTraces, isLoading: allTracesLoading } = useQuery<TraceInfo[]>({
    queryKey: ['all-traces', timeRange],
    queryFn: async () => {
      const response = await fetch(`/api/traces?time_range=${timeRange}`, {
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error('Failed to fetch traces');
      }
      return response.json();
    },
  });

  const { data: serviceTraces, isLoading: serviceTracesLoading } = useQuery<TraceInfo[]>({
    queryKey: ['service-traces', selectedService, timeRange],
    queryFn: async () => {
      const response = await fetch(`/api/services/${selectedService}/traces?time_range=${timeRange}`, {
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error('Failed to fetch service traces');
      }
      return response.json();
    },
    enabled: !!selectedService,
  });

  const traces = selectedService ? serviceTraces : allTraces;
  const isLoading = selectedService ? serviceTracesLoading : allTracesLoading;

  const uniqueServices = Array.from(
    new Set(
      (allTraces || []).flatMap(trace => trace.services_involved)
    )
  ).sort();

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-foreground">Traces</h2>
        <p className="text-sm text-muted-foreground">
          View individual traces and service interactions
        </p>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-foreground mb-2">
          Filter by Service
        </label>
        <select
          value={selectedService}
          onChange={(e) => setSelectedService(e.target.value)}
          className="w-64 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">All Services</option>
          {uniqueServices.map((service) => (
            <option key={service} value={service}>
              {service}
            </option>
          ))}
        </select>
      </div>

      {isLoading && (
        <div className="flex h-full items-center justify-center">
          <div className="text-muted-foreground">Loading traces...</div>
        </div>
      )}

      {traces && traces.length === 0 && (
        <div className="flex h-full items-center justify-center">
          <div className="text-muted-foreground">No traces found</div>
        </div>
      )}

      {traces && traces.length > 0 && (
        <div className="rounded-lg border border-border bg-card">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-foreground">Trace ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-foreground">Start Time</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-foreground">Duration</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-foreground">Spans</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-foreground">Services</th>
                </tr>
              </thead>
              <tbody>
                {traces.map((trace) => (
                  <tr
                    key={trace.trace_id}
                    className="border-b border-border hover:bg-accent/50 cursor-pointer transition-colors"
                    onClick={() => onTraceClick(trace.trace_id)}
                  >
                    <td className="px-4 py-3 text-sm font-mono text-foreground">
                      {trace.trace_id.substring(0, 16)}...
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {new Date(trace.trace_start).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-muted-foreground">
                      {trace.total_duration_ms.toFixed(2)}ms
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-muted-foreground">
                      {trace.span_count}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      <div className="flex flex-wrap gap-1">
                        {trace.services_involved.slice(0, 5).map((svc) => (
                          <span key={svc} className="inline-flex rounded px-1.5 py-0.5 text-xs bg-muted">
                            {svc}
                          </span>
                        ))}
                        {trace.services_involved.length > 5 && (
                          <span className="inline-flex rounded px-1.5 py-0.5 text-xs bg-muted">
                            +{trace.services_involved.length - 5}
                          </span>
                        )}
                      </div>
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
