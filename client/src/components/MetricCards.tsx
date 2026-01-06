import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Sparkline } from './Sparkline';
import { HistogramMetric, GaugeMetric, SumMetric, MetricValue } from '../types/metrics';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

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

  return <Icon className={`h-3 w-3 ${getColor()}`} />;
}

interface MetricRowProps {
  label: string;
  value: MetricValue;
  inverted?: boolean;
}

function MetricRow({ label, value, inverted = false }: MetricRowProps) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}:</span>
      <div className="flex items-center gap-2">
        <span className="font-medium">{value.value}{value.unit || ''}</span>
        <TrendIcon trend={value.trend} inverted={inverted} />
        {value.sparkline && value.sparkline.length > 0 && (
          <Sparkline data={value.sparkline} />
        )}
      </div>
    </div>
  );
}

interface HistogramCardProps {
  metric: HistogramMetric;
}

export function HistogramCard({ metric }: HistogramCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          📊 {metric.name}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <MetricRow label="P99" value={metric.percentiles.p99} />
        <MetricRow label="P95" value={metric.percentiles.p95} />
        <MetricRow label="P50" value={metric.percentiles.p50} />
        <MetricRow label="Avg" value={metric.percentiles.avg} />
      </CardContent>
    </Card>
  );
}

interface GaugeCardProps {
  metric: GaugeMetric;
}

export function GaugeCard({ metric }: GaugeCardProps) {
  const { current } = metric.gauge;

  // Determine health color for gauge (assuming percentage)
  const getHealthColor = (value: number) => {
    if (value > 80) return 'text-destructive';
    if (value > 60) return 'text-[hsl(30,80%,55%)]';
    return 'text-[hsl(160,60%,45%)]';
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          📈 {metric.name}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Current</div>
            <div className={`text-2xl font-bold ${getHealthColor(current.value)}`}>
              {current.value}{current.unit || '%'}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <TrendIcon trend={current.trend} inverted={true} />
            {current.sparkline && current.sparkline.length > 0 && (
              <Sparkline
                data={current.sparkline}
                color={current.value > 80 ? 'hsl(0, 84%, 60%)' :
                       current.value > 60 ? 'hsl(30, 80%, 55%)' :
                       'hsl(160, 60%, 45%)'}
                height={30}
              />
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface SumCardProps {
  metric: SumMetric;
}

export function SumCard({ metric }: SumCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          ➕ {metric.name}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Total:</span>
          <div className="flex items-center gap-2">
            <span className="font-medium">{metric.sum.total.value.toLocaleString()}</span>
            <TrendIcon trend={metric.sum.total.trend} />
          </div>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Rate:</span>
          <div className="flex items-center gap-2">
            <span className="font-medium">{metric.sum.rate.value}{metric.sum.rate.unit}</span>
            <TrendIcon trend={metric.sum.rate.trend} />
            {metric.sum.rate.sparkline && metric.sum.rate.sparkline.length > 0 && (
              <Sparkline data={metric.sum.rate.sparkline} />
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
