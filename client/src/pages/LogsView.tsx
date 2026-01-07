import { useState, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTimeRange } from '../contexts/TimeRangeContext';
import { LogsResponse, LogsFilters, LogEntry, SeverityLevel, TimeRange } from '../types/logs';
import { ServiceHealth } from '../types/observability';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Button } from '../components/ui/button';
import { LogsTable } from '../components/LogsTable';
import { SeverityFilter } from '../components/SeverityFilter';
import { SearchModeToggle } from '../components/SearchModeToggle';
import { TraceFilter } from '../components/TraceFilter';

export function LogsView() {
  const { timeRange } = useTimeRange();
  const [selectedService, setSelectedService] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');
  const [searchMode, setSearchMode] = useState<'simple' | 'advanced'>('simple');
  const [selectedSeverities, setSelectedSeverities] = useState<SeverityLevel[]>([]);
  const [traceIdFilter, setTraceIdFilter] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(100);
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);

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
    queryKey: ['services', timeRange],
    queryFn: async () => {
      const response = await fetch(`/api/services/list?time_range=${timeRange}`, {
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to fetch services');
      return response.json();
    },
  });

  // Build query params for logs
  const buildLogsQueryParams = useCallback(() => {
    const params = new URLSearchParams({
      service_name: selectedService,
      time_range: timeRange,
      search_mode: searchMode,
      page: page.toString(),
      page_size: pageSize.toString(),
    });

    if (debouncedSearch) {
      params.append('search', debouncedSearch);
    }

    if (selectedSeverities.length > 0) {
      params.append('severity_filter', selectedSeverities.join(','));
    }

    if (traceIdFilter) {
      params.append('trace_id', traceIdFilter);
    }

    return params.toString();
  }, [selectedService, timeRange, searchMode, debouncedSearch, selectedSeverities, traceIdFilter, page, pageSize]);

  // Fetch logs
  const { data: logsResponse, isLoading, error, refetch } = useQuery<LogsResponse>({
    queryKey: ['logs', selectedService, timeRange, searchMode, debouncedSearch, selectedSeverities, traceIdFilter, page, pageSize],
    queryFn: async () => {
      if (!selectedService) throw new Error('No service selected');
      const response = await fetch(
        `/api/logs/list?${buildLogsQueryParams()}`,
        { credentials: 'include' }
      );
      if (!response.ok) throw new Error('Failed to fetch logs');
      return response.json();
    },
    enabled: !!selectedService,
  });

  // Toggle severity filter
  const toggleSeverity = (severity: SeverityLevel) => {
    setSelectedSeverities((prev) =>
      prev.includes(severity)
        ? prev.filter((s) => s !== severity)
        : [...prev, severity]
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
    setSearchTerm('');
    setDebouncedSearch('');
    setSelectedSeverities([]);
    setTraceIdFilter('');
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

      {/* Filter Bar */}
      <div className="mb-4 space-y-4">
        {/* Service and Search Row */}
        <div className="flex gap-4">
          <Select value={selectedService} onValueChange={setSelectedService}>
            <SelectTrigger className="w-80">
              <SelectValue placeholder="Select a service" />
            </SelectTrigger>
            <SelectContent>
              {services?.map((service) => (
                <SelectItem key={service.service_name} value={service.service_name}>
                  {service.service_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <SearchModeToggle
            searchTerm={searchTerm}
            searchMode={searchMode}
            onSearchChange={setSearchTerm}
            onModeToggle={() => setSearchMode(searchMode === 'simple' ? 'advanced' : 'simple')}
            disabled={!selectedService}
          />
        </div>

        {/* Severity Filter and Trace ID Row */}
        {selectedService && (
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
                  setTraceIdFilter('');
                  setPage(1);
                }}
              />

              <Button variant="ghost" size="sm" onClick={clearFilters}>
                Clear All
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Loading State */}
      {isLoading && selectedService && (
        <div className="flex h-full items-center justify-center">
          <div className="text-muted-foreground">Loading logs...</div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="flex h-full items-center justify-center">
          <div className="max-w-2xl rounded-lg border border-destructive bg-destructive/10 p-4">
            <div className="text-destructive font-semibold mb-2">Failed to load logs</div>
            <div className="text-sm text-muted-foreground">{error.message}</div>
          </div>
        </div>
      )}

      {/* No Service Selected */}
      {!selectedService && !isLoading && (
        <div className="flex h-full items-center justify-center">
          <div className="max-w-2xl rounded-lg border border-border bg-card p-6 text-center">
            <div className="text-foreground font-semibold mb-2">No service selected</div>
            <div className="text-sm text-muted-foreground">
              Select a service from the dropdown above to view its logs
            </div>
          </div>
        </div>
      )}

      {/* No Logs Found */}
      {selectedService && !isLoading && !error && logsResponse && logsResponse.logs.length === 0 && (
        <div className="flex h-full items-center justify-center">
          <div className="max-w-2xl rounded-lg border border-border bg-card p-6 text-center">
            <div className="text-foreground font-semibold mb-2">No logs found</div>
            <div className="text-sm text-muted-foreground">
              {debouncedSearch || selectedSeverities.length > 0 || traceIdFilter
                ? 'Try adjusting your filters or search criteria'
                : 'No logs available for the selected service and time range'}
            </div>
          </div>
        </div>
      )}

      {/* Logs Table */}
      {selectedService && !isLoading && !error && logsResponse && logsResponse.logs.length > 0 && (
        <div className="flex-1 overflow-hidden">
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
          />
        </div>
      )}
    </div>
  );
}
