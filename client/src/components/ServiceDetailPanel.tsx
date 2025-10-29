import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { X, ArrowRight, ArrowLeft } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { ServiceMetricsDetail, TimeRange } from '../types/observability';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface DependencyInfo {
  service_name: string;
  call_count: number;
  health_status: string;
}

interface ServiceDependencies {
  service_name: string;
  inbound: DependencyInfo[];
  outbound: DependencyInfo[];
}

interface ServiceDetailPanelProps {
  serviceName: string;
  timeRange: TimeRange;
  onClose: () => void;
}

export function ServiceDetailPanel({ serviceName, timeRange, onClose }: ServiceDetailPanelProps) {
  const { data: metrics, isLoading, error } = useQuery<ServiceMetricsDetail>({
    queryKey: ['metrics', serviceName, timeRange],
    queryFn: async () => {
      const response = await fetch(`/api/services/${serviceName}/metrics?time_range=${timeRange}`, {
        credentials: 'include',
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to fetch metrics: ${response.status} - ${errorText}`);
      }
      return response.json();
    },
    refetchInterval: 30000,
    enabled: !!serviceName,
  });

  const { data: dependencies } = useQuery<ServiceDependencies>({
    queryKey: ['dependencies', serviceName],
    queryFn: async () => {
      const response = await fetch(`/api/services/${serviceName}/dependencies`, {
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error('Failed to fetch dependencies');
      }
      return response.json();
    },
    refetchInterval: 30000,
    enabled: !!serviceName,
  });

  const getChangeIndicator = (current: number, baseline: number) => {
    const change = ((current - baseline) / baseline) * 100;
    if (Math.abs(change) < 1) return { text: '~', color: 'text-muted-foreground' };
    if (change > 0) return { text: `+${change.toFixed(1)}%`, color: 'text-destructive' };
    return { text: `${change.toFixed(1)}%`, color: 'text-[hsl(160,60%,45%)]' };
  };

  return (
    <div className="fixed inset-y-0 right-0 w-full md:w-2/3 lg:w-1/2 bg-background border-l border-border shadow-xl z-50 overflow-y-auto">
      <div className="sticky top-0 bg-background border-b border-border p-4 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">{serviceName}</h2>
          <p className="text-sm text-muted-foreground">Service metrics and performance</p>
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
            <div className="text-muted-foreground">Loading metrics...</div>
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
            <div className="text-destructive font-semibold mb-2">Failed to load metrics</div>
            <div className="text-sm text-muted-foreground">{error.message}</div>
          </div>
        )}

        {metrics && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">P50 Latency</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics.current.latency_p50.toFixed(2)}ms</div>
                  <div className={`text-sm ${getChangeIndicator(metrics.current.latency_p50, metrics.baseline.latency_p50).color}`}>
                    {getChangeIndicator(metrics.current.latency_p50, metrics.baseline.latency_p50).text} vs baseline
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">P95 Latency</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics.current.latency_p95.toFixed(2)}ms</div>
                  <div className={`text-sm ${getChangeIndicator(metrics.current.latency_p95, metrics.baseline.latency_p95).color}`}>
                    {getChangeIndicator(metrics.current.latency_p95, metrics.baseline.latency_p95).text} vs baseline
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">P99 Latency</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics.current.latency_p99.toFixed(2)}ms</div>
                  <div className={`text-sm ${getChangeIndicator(metrics.current.latency_p99, metrics.baseline.latency_p99).color}`}>
                    {getChangeIndicator(metrics.current.latency_p99, metrics.baseline.latency_p99).text} vs baseline
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Error Rate</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{(metrics.current.error_rate * 100).toFixed(2)}%</div>
                  <div className={`text-sm ${getChangeIndicator(metrics.current.error_rate, metrics.baseline.error_rate).color}`}>
                    {getChangeIndicator(metrics.current.error_rate, metrics.baseline.error_rate).text} vs baseline
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Avg Duration</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics.current.avg_duration_ms.toFixed(2)}ms</div>
                  <div className={`text-sm ${getChangeIndicator(metrics.current.avg_duration_ms, metrics.baseline.avg_duration_ms).color}`}>
                    {getChangeIndicator(metrics.current.avg_duration_ms, metrics.baseline.avg_duration_ms).text} vs baseline
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Requests/sec</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics.current.requests_per_second.toFixed(2)}</div>
                  <div className={`text-sm ${getChangeIndicator(metrics.current.requests_per_second, metrics.baseline.requests_per_second).color}`}>
                    {getChangeIndicator(metrics.current.requests_per_second, metrics.baseline.requests_per_second).text} vs baseline
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>P95 Latency Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={metrics.trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis 
                      dataKey="timestamp" 
                      stroke="hsl(var(--muted-foreground))"
                      tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    />
                    <YAxis stroke="hsl(var(--muted-foreground))" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '0.5rem'
                      }}
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="latency_p95" stroke="hsl(160 60% 45%)" name="P95 Latency (ms)" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Average Duration Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={metrics.trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis 
                      dataKey="timestamp" 
                      stroke="hsl(var(--muted-foreground))"
                      tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    />
                    <YAxis stroke="hsl(var(--muted-foreground))" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '0.5rem'
                      }}
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="avg_duration_ms" stroke="hsl(30 80% 55%)" name="Avg Duration (ms)" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Error Count Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={metrics.trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis 
                      dataKey="timestamp" 
                      stroke="hsl(var(--muted-foreground))"
                      tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    />
                    <YAxis stroke="hsl(var(--muted-foreground))" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '0.5rem'
                      }}
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="error_count" stroke="hsl(0 63% 31%)" name="Error Count" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Request Count Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={metrics.trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis 
                      dataKey="timestamp" 
                      stroke="hsl(var(--muted-foreground))"
                      tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    />
                    <YAxis stroke="hsl(var(--muted-foreground))" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '0.5rem'
                      }}
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="request_count" stroke="hsl(200 80% 50%)" name="Request Count" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {dependencies && (dependencies.inbound.length > 0 || dependencies.outbound.length > 0) && (
              <Card>
                <CardHeader>
                  <CardTitle>Service Dependencies</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    {dependencies.inbound.length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                          <ArrowLeft className="h-4 w-4" />
                          Inbound ({dependencies.inbound.length})
                        </h3>
                        <div className="space-y-2">
                          {dependencies.inbound.map((dep) => (
                            <div
                              key={dep.service_name}
                              className="flex items-center justify-between p-3 rounded-lg border border-border bg-card hover:bg-accent/50 transition-colors"
                            >
                              <div className="flex items-center gap-3">
                                <span className="text-sm font-medium text-foreground">{dep.service_name}</span>
                                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                                  dep.health_status === 'critical' ? 'bg-destructive text-destructive-foreground' :
                                  dep.health_status === 'warning' ? 'bg-[hsl(30,80%,55%)] text-primary-foreground' :
                                  'bg-[hsl(160,60%,45%)] text-primary-foreground'
                                }`}>
                                  {dep.health_status}
                                </span>
                              </div>
                              <span className="text-sm text-muted-foreground">{dep.call_count.toLocaleString()} calls</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {dependencies.outbound.length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                          <ArrowRight className="h-4 w-4" />
                          Outbound ({dependencies.outbound.length})
                        </h3>
                        <div className="space-y-2">
                          {dependencies.outbound.map((dep) => (
                            <div
                              key={dep.service_name}
                              className="flex items-center justify-between p-3 rounded-lg border border-border bg-card hover:bg-accent/50 transition-colors"
                            >
                              <div className="flex items-center gap-3">
                                <span className="text-sm font-medium text-foreground">{dep.service_name}</span>
                                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                                  dep.health_status === 'critical' ? 'bg-destructive text-destructive-foreground' :
                                  dep.health_status === 'warning' ? 'bg-[hsl(30,80%,55%)] text-primary-foreground' :
                                  'bg-[hsl(160,60%,45%)] text-primary-foreground'
                                }`}>
                                  {dep.health_status}
                                </span>
                              </div>
                              <span className="text-sm text-muted-foreground">{dep.call_count.toLocaleString()} calls</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

          </>
        )}
      </div>
    </div>
  );
}
