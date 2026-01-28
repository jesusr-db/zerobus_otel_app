import { LogEntry, SeverityLevel } from "../types/logs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { ChevronLeft, ChevronRight, Link2 } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./ui/tooltip";

interface LogsTableProps {
  logs: LogEntry[];
  totalCount: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  onLogSelect: (log: LogEntry | null) => void;
  selectedLog: LogEntry | null;
  onTraceClick: (traceId: string) => void;
}

export function LogsTable({
  logs,
  totalCount,
  page,
  pageSize,
  hasMore,
  onPageChange,
  onPageSizeChange,
  onLogSelect,
  selectedLog,
  onTraceClick,
}: LogsTableProps) {
  // Severity colors
  const getSeverityColor = (severity: SeverityLevel) => {
    switch (severity) {
      case "ERROR":
        return "hsl(0, 84%, 60%)";
      case "WARN":
        return "hsl(30, 80%, 55%)";
      case "INFO":
        return "hsl(160, 60%, 45%)";
      case "DEBUG":
        return "hsl(var(--muted-foreground))";
      default:
        return "hsl(var(--muted-foreground))";
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      fractionalSecondDigits: 3,
    });
  };

  // Truncate message
  const truncateMessage = (message: string, maxLength: number = 80) => {
    if (message.length <= maxLength) return message;
    return message.substring(0, maxLength) + "...";
  };

  // Calculate pagination
  const startItem = (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, totalCount);
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="flex h-full flex-col">
      {/* Table */}
      <div className="flex-1 overflow-auto border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[180px]">Timestamp</TableHead>
              <TableHead className="w-[100px]">Severity</TableHead>
              <TableHead className="w-[150px]">Service</TableHead>
              <TableHead>Message</TableHead>
              <TableHead className="w-[80px] text-center">Trace</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {logs.map((log) => {
              const isSelected =
                selectedLog?.log_timestamp === log.log_timestamp &&
                selectedLog?.body === log.body;
              const severityColor = getSeverityColor(log.severity_text);

              return (
                <TableRow
                  key={`${log.log_timestamp}-${log.body}`}
                  className={`cursor-pointer hover:bg-muted/50 ${
                    isSelected ? "bg-muted" : ""
                  }`}
                  style={{
                    borderLeft: `4px solid ${severityColor}`,
                  }}
                  onClick={() => onLogSelect(isSelected ? null : log)}
                >
                  <TableCell className="font-mono text-xs text-foreground">
                    {formatTimestamp(log.log_timestamp)}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      style={{
                        backgroundColor: `${severityColor}20`,
                        borderColor: severityColor,
                        color: severityColor,
                      }}
                    >
                      {log.severity_text}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-foreground">
                    {log.service_name}
                  </TableCell>
                  <TableCell className="text-sm text-foreground">
                    {truncateMessage(log.body)}
                  </TableCell>
                  <TableCell
                    className="text-center"
                    onClick={(e) => {
                      // Prevent row click when clicking in this cell
                      if (log.trace_id && log.trace_id !== "") {
                        e.stopPropagation();
                      }
                    }}
                  >
                    {log.trace_id && log.trace_id !== "" && (
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                onTraceClick(log.trace_id);
                              }}
                              className="inline-flex items-center justify-center hover:bg-muted rounded p-1 transition-colors"
                            >
                              {/* Trace icon - currently filters by trace_id */}
                              {/* Future: Link to distributed trace visualization (waterfall/flame graph) */}
                              <Link2 className="h-4 w-4 text-primary hover:text-primary/80" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="text-xs">Filter by this trace ID</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Pagination Controls */}
      <div className="flex items-center justify-between border-t bg-card p-4 mt-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Rows per page:
            </span>
            <Select
              value={pageSize.toString()}
              onValueChange={(value) => onPageSizeChange(Number(value))}
            >
              <SelectTrigger className="w-[80px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="50">50</SelectItem>
                <SelectItem value="100">100</SelectItem>
                <SelectItem value="500">500</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="text-sm text-muted-foreground">
            Showing {startItem}-{endItem} of {totalCount.toLocaleString()} logs
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Previous
          </Button>

          <div className="flex items-center gap-1">
            <span className="text-sm text-muted-foreground">
              Page {page} of {totalPages}
            </span>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={!hasMore}
          >
            Next
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </div>
    </div>
  );
}
