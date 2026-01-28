import { useQuery } from "@tanstack/react-query";
import { TimeRange } from "../types/logs";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface SeverityTimelinePoint {
  timestamp: string;
  ERROR: number;
  WARN: number;
  INFO: number;
  DEBUG: number;
}

interface SeverityTimelineResponse {
  timeline: SeverityTimelinePoint[];
  service_name: string;
  time_range: string;
}

interface SeverityTimelineProps {
  serviceName?: string;
  timeRange: TimeRange;
}

export function SeverityTimeline({
  serviceName,
  timeRange,
}: SeverityTimelineProps) {
  // Fetch timeline data
  const { data, isLoading, error } = useQuery<SeverityTimelineResponse>({
    queryKey: ["severity-timeline", serviceName, timeRange],
    queryFn: async () => {
      const params = new URLSearchParams({
        time_range: timeRange,
      });

      if (serviceName && serviceName !== "__ALL__") {
        params.append("service_name", serviceName);
      }

      const response = await fetch(
        `/api/logs/severity-timeline?${params.toString()}`,
        {
          credentials: "include",
        },
      );

      if (!response.ok) throw new Error("Failed to fetch severity timeline");
      return response.json();
    },
  });

  // Format timestamp for display
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Transform data for Recharts
  const chartData =
    data?.timeline.map((point) => ({
      time: formatTime(point.timestamp),
      ERROR: point.ERROR,
      WARN: point.WARN,
      INFO: point.INFO,
      DEBUG: point.DEBUG,
    })) || [];

  if (isLoading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <div className="text-sm text-muted-foreground">Loading timeline...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-64 flex items-center justify-center">
        <div className="text-sm text-destructive">Failed to load timeline</div>
      </div>
    );
  }

  if (!chartData || chartData.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center">
        <div className="text-sm text-muted-foreground">
          No timeline data available
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorError" x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="5%"
                stopColor="hsl(0, 84%, 60%)"
                stopOpacity={0.8}
              />
              <stop
                offset="95%"
                stopColor="hsl(0, 84%, 60%)"
                stopOpacity={0.1}
              />
            </linearGradient>
            <linearGradient id="colorWarn" x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="5%"
                stopColor="hsl(30, 80%, 55%)"
                stopOpacity={0.8}
              />
              <stop
                offset="95%"
                stopColor="hsl(30, 80%, 55%)"
                stopOpacity={0.1}
              />
            </linearGradient>
            <linearGradient id="colorInfo" x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="5%"
                stopColor="hsl(160, 60%, 45%)"
                stopOpacity={0.8}
              />
              <stop
                offset="95%"
                stopColor="hsl(160, 60%, 45%)"
                stopOpacity={0.1}
              />
            </linearGradient>
            <linearGradient id="colorDebug" x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="5%"
                stopColor="hsl(var(--muted-foreground))"
                stopOpacity={0.6}
              />
              <stop
                offset="95%"
                stopColor="hsl(var(--muted-foreground))"
                stopOpacity={0.1}
              />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis
            dataKey="time"
            stroke="hsl(var(--muted-foreground))"
            fontSize={12}
            tickLine={false}
          />
          <YAxis
            stroke="hsl(var(--muted-foreground))"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "8px",
            }}
            labelStyle={{ color: "hsl(var(--foreground))" }}
          />
          <Legend />
          <Area
            type="monotone"
            dataKey="ERROR"
            stackId="1"
            stroke="hsl(0, 84%, 60%)"
            fill="url(#colorError)"
            strokeWidth={2}
          />
          <Area
            type="monotone"
            dataKey="WARN"
            stackId="1"
            stroke="hsl(30, 80%, 55%)"
            fill="url(#colorWarn)"
            strokeWidth={2}
          />
          <Area
            type="monotone"
            dataKey="INFO"
            stackId="1"
            stroke="hsl(160, 60%, 45%)"
            fill="url(#colorInfo)"
            strokeWidth={2}
          />
          <Area
            type="monotone"
            dataKey="DEBUG"
            stackId="1"
            stroke="hsl(var(--muted-foreground))"
            fill="url(#colorDebug)"
            strokeWidth={1}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
