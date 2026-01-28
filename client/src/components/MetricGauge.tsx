import { TimeSeriesPoint } from "../types/metrics";
import { MetricLineChart } from "./MetricLineChart";

interface MetricGaugeProps {
  value: number;
  unit?: string;
  timeseries?: TimeSeriesPoint[];
}

export function MetricGauge({
  value,
  unit = "%",
  timeseries,
}: MetricGaugeProps) {
  // Determine color based on value (assuming percentage)
  const getColor = () => {
    if (value > 80) return "hsl(0, 84%, 60%)"; // Red
    if (value > 60) return "hsl(30, 80%, 55%)"; // Yellow
    return "hsl(160, 60%, 45%)"; // Green
  };

  const color = getColor();
  const percentage = Math.min(Math.max(value, 0), 100);

  return (
    <div className="space-y-4">
      {/* Circular gauge visualization */}
      <div className="flex items-center justify-center">
        <div className="relative w-32 h-32">
          <svg className="w-full h-full transform -rotate-90">
            {/* Background circle */}
            <circle
              cx="64"
              cy="64"
              r="56"
              fill="none"
              stroke="hsl(var(--muted))"
              strokeWidth="12"
            />
            {/* Value arc */}
            <circle
              cx="64"
              cy="64"
              r="56"
              fill="none"
              stroke={color}
              strokeWidth="12"
              strokeDasharray={`${(percentage / 100) * 351.858} 351.858`}
              strokeLinecap="round"
              className="transition-all duration-500"
            />
          </svg>
          {/* Center value */}
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-3xl font-bold" style={{ color }}>
              {value.toFixed(1)}
              {unit}
            </span>
          </div>
        </div>
      </div>

      {/* Time series chart if available */}
      {timeseries && timeseries.length > 0 && (
        <div className="mt-4">
          <MetricLineChart data={timeseries} color={color} height={120} />
        </div>
      )}
    </div>
  );
}
