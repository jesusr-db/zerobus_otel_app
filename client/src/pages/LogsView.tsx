import { useState, useCallback, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTimeRange } from "../contexts/TimeRangeContext";
import {
  LogsResponse,
  LogsFilters,
  LogEntry,
  SeverityLevel,
  TimeRange,
} from "../types/logs";
import { ServiceHealth } from "../types/observability";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Button } from "../components/ui/button";
import { LogsTable } from "../components/LogsTable";
import { SeverityFilter } from "../components/SeverityFilter";
import { SearchModeToggle } from "../components/SearchModeToggle";
import { TraceFilter } from "../components/TraceFilter";
import { LogDetailsPanel } from "../components/LogDetailsPanel";
import { SeverityTimeline } from "../components/SeverityTimeline";
import { ChevronDown, ChevronUp } from "lucide-react";

export function LogsView() {
  const { timeRange } = useTimeRange();
  const [selectedService, setSelectedService] = useState<string>("__ALL__");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");
  const [searchMode, setSearchMode] = useState<"simple" | "advanced">("simple");
  const [selectedSeverities, setSelectedSeverities] = useState<SeverityLevel[]>(
    [],
  );
  const [traceIdFilter, setTraceIdFilter] = useState<string>("");
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(100);
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [timelineCollapsed, setTimelineCollapsed] = useState<boolean>(false);

  // Debounce search input (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setPage(1); // Reset to page 1 when search changes
    }, 300);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Fetch available services
  const { data: services } = useQuery<ServiceHealth[]>({
    queryKey: ["services", timeRange],
    queryFn: async () => {
      const response = await fetch(
        `/api/services/list?time_range=${timeRange}`,
        {
          credentials: "include",
        },
      );
      if (!response.ok) throw new Error("Failed to fetch services");
      return response.json();
    },
  });

  // Build query params for logs
  const buildLogsQueryParams = useCallback(() => {
    const params = new URLSearchParams({
      time_range: timeRange,
      search_mode: searchMode,
      page: page.toString(),
      page_size: pageSize.toString(),
    });

    if (selectedService && selectedService !== "__ALL__") {
      params.append("service_name", selectedService);
    }

    if (debouncedSearch) {
      params.append("search", debouncedSearch);
    }

    if (selectedSeverities.length > 0) {
      params.append("severity_filter", selectedSeverities.join(","));
    }

    if (traceIdFilter) {
      params.append("trace_id", traceIdFilter);
    }

    return params.toString();
  }, [
    selectedService,
    timeRange,
    searchMode,
    debouncedSearch,
    selectedSeverities,
    traceIdFilter,
    page,
    pageSize,
  ]);

  // Fetch logs (service is optional - searches all services if not specified)
  const {
    data: logsResponse,
    isLoading,
    error,
    refetch,
  } = useQuery<LogsResponse>({
    queryKey: [
      "logs",
      selectedService,
      timeRange,
      searchMode,
      debouncedSearch,
      selectedSeverities,
      traceIdFilter,
      page,
      pageSize,
    ],
    queryFn: async () => {
      const response = await fetch(`/api/logs/list?${buildLogsQueryParams()}`, {
        credentials: "include",
      });
      if (!response.ok) throw new Error("Failed to fetch logs");
      return response.json();
    },
    enabled: true,
  });

  // Toggle severity filter
  const toggleSeverity = (severity: SeverityLevel) => {
    setSelectedSeverities((prev) =>
      prev.includes(severity)
        ? prev.filter((s) => s !== severity)
        : [...prev, severity],
    );
    setPage(1); // Reset to page 1 when filters change
  };

  // Clear severity filters
  const clearSeverityFilters = () => {
    setSelectedSeverities([]);
    setPage(1);
  };

  // Clear all filters
  const clearFilters = () => {
    setSearchTerm("");
    setDebouncedSearch("");
    setSelectedSeverities([]);
    setTraceIdFilter("");
    setPage(1);
  };

  // Get severity counts from response
  const severityCounts = logsResponse?.severity_counts || {};

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-foreground">Logs</h2>
        <p className="text-sm text-muted-foreground">
          Search and analyze service logs for troubleshooting
        </p>
      </div>

      {/* Severity Timeline - Collapsible */}
      <div className="mb-6 rounded-lg border border-border bg-card">
        <div
          className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/50 transition-colors"
          onClick={() => setTimelineCollapsed(!timelineCollapsed)}
        >
          <div>
            <h3 className="text-lg font-semibold text-foreground">
              Severity Distribution Over Time
            </h3>
            <p className="text-sm text-muted-foreground">
              {selectedService && selectedService !== "__ALL__"
                ? `${selectedService} - `
                : "All Services - "}
              Last {timeRange}
            </p>
          </div>
          <Button variant="ghost" size="sm">
            {timelineCollapsed ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronUp className="h-4 w-4" />
            )}
          </Button>
        </div>

        {!timelineCollapsed && (
          <div className="px-4 pb-4 animate-in fade-in slide-in-from-top-2 duration-200">
            <SeverityTimeline
              serviceName={selectedService}
              timeRange={timeRange as TimeRange}
            />
          </div>
        )}
      </div>

      {/* Filter Bar */}
      <div className="mb-4 space-y-4">
        {/* Service and Search Row */}
        <div className="flex gap-4">
          <Select value={selectedService} onValueChange={setSelectedService}>
            <SelectTrigger className="w-80">
              <SelectValue placeholder="All Services" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__ALL__">All Services</SelectItem>
              {services?.map((service) => (
                <SelectItem
                  key={service.service_name}
                  value={service.service_name}
                >
                  {service.service_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <SearchModeToggle
            searchTerm={searchTerm}
            searchMode={searchMode}
            onSearchChange={setSearchTerm}
            onModeToggle={() =>
              setSearchMode(searchMode === "simple" ? "advanced" : "simple")
            }
          />
        </div>

        {/* Severity Filter and Trace ID Row */}
        <div className="flex gap-4 items-center justify-between">
          <SeverityFilter
            selectedSeverities={selectedSeverities}
            severityCounts={severityCounts}
            onToggleSeverity={toggleSeverity}
            onClearAll={clearSeverityFilters}
          />

          <div className="flex gap-3 items-center">
            <TraceFilter
              traceId={traceIdFilter}
              onChange={(value) => {
                setTraceIdFilter(value);
                setPage(1);
              }}
              onClear={() => {
                setTraceIdFilter("");
                setPage(1);
              }}
            />

            <Button variant="ghost" size="sm" onClick={clearFilters}>
              Clear All
            </Button>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex h-full items-center justify-center">
          <div className="text-muted-foreground">Loading logs...</div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="flex h-full items-center justify-center">
          <div className="max-w-2xl rounded-lg border border-destructive bg-destructive/10 p-4">
            <div className="text-destructive font-semibold mb-2">
              Failed to load logs
            </div>
            <div className="text-sm text-muted-foreground">{error.message}</div>
          </div>
        </div>
      )}

      {/* No Logs Found */}
      {!isLoading &&
        !error &&
        logsResponse &&
        logsResponse.logs.length === 0 && (
          <div className="flex h-full items-center justify-center">
            <div className="max-w-2xl rounded-lg border border-border bg-card p-6 text-center">
              <div className="text-foreground font-semibold mb-2">
                No logs found
              </div>
              <div className="text-sm text-muted-foreground">
                {debouncedSearch ||
                selectedSeverities.length > 0 ||
                traceIdFilter
                  ? "Try adjusting your filters or search criteria"
                  : selectedService && selectedService !== "__ALL__"
                    ? "No logs available for the selected service and time range"
                    : "No logs available for the selected time range"}
              </div>
            </div>
          </div>
        )}

      {/* Logs Table and Details Panel */}
      {!isLoading && !error && logsResponse && logsResponse.logs.length > 0 && (
        <div className="flex-1 overflow-hidden flex gap-4">
          {/* Table - takes full width when no log selected, half when log selected */}
          <div
            className={`flex-1 overflow-hidden transition-all ${selectedLog ? "w-1/2" : "w-full"}`}
          >
            <LogsTable
              logs={logsResponse.logs}
              totalCount={logsResponse.total_count}
              page={page}
              pageSize={pageSize}
              hasMore={logsResponse.has_more}
              onPageChange={setPage}
              onPageSizeChange={(newSize) => {
                setPageSize(newSize);
                setPage(1);
              }}
              onLogSelect={setSelectedLog}
              selectedLog={selectedLog}
              onTraceClick={(traceId) => {
                setTraceIdFilter(traceId);
                setPage(1);
              }}
            />
          </div>

          {/* Details Panel - slides in from right when log selected */}
          {selectedLog && (
            <div className="w-1/2 overflow-hidden animate-in slide-in-from-right duration-200">
              <LogDetailsPanel
                log={selectedLog}
                onClose={() => setSelectedLog(null)}
                onViewTrace={(traceId) => {
                  setTraceIdFilter(traceId);
                  setPage(1);
                  setSelectedLog(null); // Close panel to show filtered results
                }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
