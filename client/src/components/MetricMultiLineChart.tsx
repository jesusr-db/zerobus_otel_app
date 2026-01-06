import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface DataSeries {
  name: string;
  data: Array<{ time: string; value: number }>;
  color: string;
}

interface MetricMultiLineChartProps {
  series: DataSeries[];
  height?: number;
}

export function MetricMultiLineChart({ series, height = 250 }: MetricMultiLineChartProps) {
  if (!series || series.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 bg-muted/20 rounded">
        <span className="text-sm text-muted-foreground">No data available</span>
      </div>
    );
  }

  // Merge all time series into a single dataset
  const mergedData: Record<string, any> = {};

  series.forEach((s) => {
    s.data.forEach((point) => {
      const timeKey = point.time;
      if (!mergedData[timeKey]) {
        mergedData[timeKey] = { time: timeKey };
      }
      mergedData[timeKey][s.name] = point.value;
    });
  });

  const chartData = Object.values(mergedData).sort((a, b) =>
    new Date(a.time).getTime() - new Date(b.time).getTime()
  );

  // Format timestamp for display
  const formatTime = (time: string) => {
    const date = new Date(time);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const fullDate = new Date(data.time);
      return (
        <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
          <p className="text-xs text-muted-foreground mb-2">
            {fullDate.toLocaleString('en-US', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}
          </p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm font-semibold" style={{ color: entry.color }}>
              {entry.name}: {entry.value?.toFixed(2) || 'N/A'}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
        <XAxis
          dataKey="time"
          tickFormatter={formatTime}
          stroke="hsl(var(--muted-foreground))"
          tick={{ fontSize: 11 }}
          tickLine={false}
        />
        <YAxis
          stroke="hsl(var(--muted-foreground))"
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: '12px' }}
          iconType="line"
        />
        {series.map((s) => (
          <Line
            key={s.name}
            type="monotone"
            dataKey={s.name}
            stroke={s.color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            name={s.name}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
