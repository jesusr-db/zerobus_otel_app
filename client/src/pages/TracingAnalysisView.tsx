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

interface SpanWaterfall {
  span_id: string;
  name: string;
  service_name: string;
  duration_ms: number;
  start_offset_ms: number;
  parent_span_id: string | null;
  is_error: boolean;
}

interface TraceWaterfall {
  trace_id: string;
  trace_start: string;
  total_duration_ms: number;
  spans: SpanWaterfall[];
}

const COLORS = [
  'bg-green-500',
  'bg-blue-500',
  'bg-purple-500',
  'bg-yellow-500',
  'bg-pink-500',
  'bg-indigo-500',
  'bg-cyan-500',
  'bg-teal-500',
];

export function TracingAnalysisView() {
  const { timeRange } = useTimeRange();
  const [selectedService, setSelectedService] = useState<string>('');
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);

  const { data: allTraces, isLoading: allTracesLoading, error: tracesError } = useQuery<TraceInfo[]>({
    queryKey: ['all-traces-analysis', timeRange],
    queryFn: async () => {
      const response = await fetch(`/api/traces?time_range=${timeRange}`, {
        credentials: 'include',
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Failed to fetch traces');
      }
      const data = await response.json();
      return data;
    },
    retry: 1,
  });

  const { data: waterfallData, isLoading: waterfallLoading } = useQuery<TraceWaterfall>({
    queryKey: ['trace-waterfall', selectedTraceId],
    queryFn: async () => {
      const response = await fetch(`/api/traces/waterfall/${selectedTraceId}`, {
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error('Failed to fetch trace waterfall');
      }
      return response.json();
    },
    enabled: !!selectedTraceId,
  });

  const filteredTraces = selectedService
    ? allTraces?.filter(trace => trace.services_involved.includes(selectedService))
    : allTraces;

  const uniqueServices = Array.from(
    new Set(
      (allTraces || []).flatMap(trace => trace.services_involved)
    )
  ).sort();

  const buildSpanHierarchy = (spans: SpanWaterfall[]) => {
    const spanMap = new Map(spans.map(s => [s.span_id, { ...s, children: [] as SpanWaterfall[], depth: 0 }]));
    const roots: any[] = [];
    
    spans.forEach(span => {
      const node = spanMap.get(span.span_id)!;
      if (!span.parent_span_id || !spanMap.has(span.parent_span_id)) {
        roots.push(node);
      } else {
        const parent = spanMap.get(span.parent_span_id);
        if (parent) {
          parent.children.push(node);
        }
      }
    });
    
    const setDepth = (node: any, depth: number) => {
      node.depth = depth;
      node.children.forEach((child: any) => setDepth(child, depth + 1));
    };
    
    roots.forEach(root => setDepth(root, 0));
    
    const flatten = (node: any): any[] => {
      return [node, ...node.children.flatMap(flatten)];
    };
    
    return roots.flatMap(flatten);
  };

  const getServiceColor = (serviceName: string, services: string[]) => {
    const index = services.indexOf(serviceName);
    return COLORS[index % COLORS.length];
  };

  const renderWaterfallSpan = (
    span: SpanWaterfall & { depth: number },
    totalDuration: number,
    servicesList: string[]
  ) => {
    const leftPercent = (span.start_offset_ms / totalDuration) * 100;
    const widthPercent = (span.duration_ms / totalDuration) * 100;
    const indentPx = span.depth * 24;
    
    const colorClass = span.is_error 
      ? 'bg-red-500' 
      : getServiceColor(span.service_name, servicesList);

    return (
      <div key={span.span_id} className="mb-1 relative">
        <div className="flex items-center gap-2 text-xs mb-1" style={{ paddingLeft: `${indentPx}px` }}>
          {span.depth > 0 && (
            <span className="text-muted-foreground">└─</span>
          )}
          <span className="w-32 truncate font-medium text-foreground" title={span.service_name}>
            {span.service_name}
          </span>
          <span className="flex-1 truncate text-muted-foreground" title={span.name}>
            {span.name}
          </span>
          <span className="w-24 text-right text-foreground font-mono text-xs">
            {span.duration_ms.toFixed(2)}ms
          </span>
        </div>
        
        <div className="h-10 relative" style={{ paddingLeft: `${indentPx}px` }}>
          <div className="h-full bg-muted/30 rounded relative">
            <div
              className={`absolute ${colorClass} hover:opacity-90 transition-all rounded flex items-center justify-between px-2 text-xs font-medium text-white overflow-hidden shadow-sm`}
              style={{
                left: `${leftPercent}%`,
                width: `${Math.max(widthPercent, 1)}%`,
                height: '32px',
                top: '4px',
              }}
              title={`${span.service_name} - ${span.name}\nStart: ${span.start_offset_ms.toFixed(2)}ms\nDuration: ${span.duration_ms.toFixed(2)}ms`}
            >
              <span className="truncate">{span.name}</span>
              {widthPercent > 10 && (
                <span className="ml-2 opacity-90">{span.duration_ms.toFixed(1)}ms</span>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-foreground">Tracing Analysis</h2>
        <p className="text-sm text-muted-foreground">
          Visualize trace spans in waterfall format with parent-child relationships
        </p>
      </div>

      <div className="mb-4 flex gap-4">
        <div>
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
      </div>

      {allTracesLoading && (
        <div className="flex h-full items-center justify-center">
          <div className="text-muted-foreground">Loading traces...</div>
        </div>
      )}

      {tracesError && (
        <div className="flex h-full items-center justify-center">
          <div className="text-red-500">Error loading traces: {tracesError.message}</div>
        </div>
      )}

      <div className="flex gap-6 flex-1 overflow-hidden">
        <div className="w-1/3 overflow-auto">
          <h3 className="text-lg font-semibold text-foreground mb-3">Traces</h3>
          
          {filteredTraces && filteredTraces.length === 0 && (
            <div className="flex items-center justify-center h-32">
              <div className="text-muted-foreground">No traces found</div>
            </div>
          )}

          {filteredTraces && filteredTraces.length > 0 && (
            <div className="space-y-2">
              {filteredTraces.map((trace) => (
                <div
                  key={trace.trace_id}
                  onClick={() => setSelectedTraceId(trace.trace_id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedTraceId === trace.trace_id
                      ? 'border-primary bg-accent'
                      : 'border-border bg-card hover:bg-accent/50'
                  }`}
                >
                  <div className="text-sm font-mono text-foreground mb-1">
                    {trace.trace_id.substring(0, 16)}...
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {new Date(trace.trace_start).toLocaleString()}
                  </div>
                  <div className="flex justify-between mt-2 text-xs">
                    <span className="text-muted-foreground">{trace.span_count} spans</span>
                    <span className="text-muted-foreground">{trace.total_duration_ms.toFixed(2)}ms</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-auto">
          {!selectedTraceId && (
            <div className="flex items-center justify-center h-full">
              <div className="text-muted-foreground">Select a trace to view waterfall</div>
            </div>
          )}

          {selectedTraceId && waterfallLoading && (
            <div className="flex items-center justify-center h-full">
              <div className="text-muted-foreground">Loading waterfall...</div>
            </div>
          )}

          {selectedTraceId && waterfallData && (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  Trace Waterfall
                </h3>
                <div className="text-sm text-muted-foreground space-y-1">
                  <div>Trace ID: <span className="font-mono">{waterfallData.trace_id}</span></div>
                  <div>Start: {new Date(waterfallData.trace_start).toLocaleString()}</div>
                  <div>Total Duration: {waterfallData.total_duration_ms.toFixed(2)}ms</div>
                  <div>Spans: {waterfallData.spans.length}</div>
                </div>
              </div>

              <div className="rounded-lg border border-border bg-card p-4">
                <div className="mb-4 flex items-center justify-between text-xs text-muted-foreground border-b border-border pb-2">
                  <span>0ms</span>
                  <span className="font-medium">Time →</span>
                  <span>{waterfallData.total_duration_ms.toFixed(2)}ms</span>
                </div>
                
                {(() => {
                  const hierarchicalSpans = buildSpanHierarchy(waterfallData.spans);
                  const servicesList = Array.from(new Set(waterfallData.spans.map(s => s.service_name))).sort();
                  
                  return (
                    <>
                      <div className="mb-4 flex flex-wrap gap-2">
                        {servicesList.map((service) => (
                          <div key={service} className="flex items-center gap-2 text-xs">
                            <div className={`w-3 h-3 rounded ${getServiceColor(service, servicesList)}`} />
                            <span className="text-foreground">{service}</span>
                          </div>
                        ))}
                      </div>
                      
                      {hierarchicalSpans.map((span) =>
                        renderWaterfallSpan(span, waterfallData.total_duration_ms, servicesList)
                      )}
                    </>
                  );
                })()}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
