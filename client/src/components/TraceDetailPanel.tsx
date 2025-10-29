import { useQuery } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

interface SpanDetail {
  service_name: string;
  total_duration_ms: number;
}

interface TraceDetail {
  trace_id: string;
  trace_start: string;
  spans: SpanDetail[];
}

interface TraceDetailPanelProps {
  traceId: string;
  onClose: () => void;
}

export function TraceDetailPanel({ traceId, onClose }: TraceDetailPanelProps) {
  const { data: trace, isLoading, error } = useQuery<TraceDetail>({
    queryKey: ['trace-detail', traceId],
    queryFn: async () => {
      const response = await fetch(`/api/services/traces/${traceId}`, {
        credentials: 'include',
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to fetch trace: ${response.status} - ${errorText}`);
      }
      return response.json();
    },
    enabled: !!traceId,
  });

  return (
    <div className="fixed inset-y-0 right-0 w-full md:w-1/3 lg:w-1/4 bg-background border-l border-border shadow-xl z-[60] overflow-y-auto">
      <div className="sticky top-0 bg-background border-b border-border p-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-foreground">Trace Details</h2>
          <p className="text-xs text-muted-foreground font-mono">{traceId}</p>
        </div>
        <button
          onClick={onClose}
          className="rounded-full p-2 hover:bg-accent transition-colors text-muted-foreground hover:text-foreground"
          aria-label="Close panel"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="p-6 space-y-6">
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-muted-foreground">Loading trace details...</div>
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
            <div className="text-destructive font-semibold mb-2">Failed to load trace</div>
            <div className="text-sm text-muted-foreground">{error.message}</div>
          </div>
        )}

        {trace && (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Trace Information</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Start Time:</span>
                    <span className="font-medium">{new Date(trace.trace_start).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total Services:</span>
                    <span className="font-medium">{trace.spans.length}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Service Duration Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {trace.spans.map((span) => (
                    <div
                      key={span.service_name}
                      className="flex items-center justify-between p-3 rounded-lg border border-border bg-card"
                    >
                      <span className="text-sm font-medium text-foreground">{span.service_name}</span>
                      <span className="text-sm text-muted-foreground">{span.total_duration_ms.toFixed(2)}ms</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
