/**
 * TypeScript types for Logs API
 */

export type SeverityLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'FATAL';

export type TimeRange = '5m' | '1h' | '1d' | '1w';

export type SearchMode = 'simple' | 'advanced';

export interface LogEntry {
  event_name: string;
  trace_id: string;
  span_id: string;
  log_timestamp: string;        // ISO 8601 timestamp
  observed_timestamp: string;   // ISO 8601 timestamp
  severity_text: SeverityLevel | string;  // Can be any string if not one of the standard levels
  body: string;
  service_name: string;
  attributes: Record<string, any>;  // Parsed from JSON string
}

export interface LogsResponse {
  logs: LogEntry[];
  total_count: number;
  page: number;
  page_size: number;
  has_more: boolean;
  severity_counts: Record<string, number>;
}

export interface SeverityTimelinePoint {
  timestamp: string;  // ISO 8601 timestamp
  ERROR: number;
  WARN: number;
  INFO: number;
  DEBUG: number;
}

export interface SeverityTimelineResponse {
  timeline: SeverityTimelinePoint[];
  service_name: string;
  time_range: string;
}

export interface LogsFilters {
  service_name: string;
  time_range: TimeRange;
  search?: string;
  search_mode: SearchMode;
  severity_filter?: string;  // Comma-separated severity levels
  trace_id?: string;
  page: number;
  page_size: number;
}
