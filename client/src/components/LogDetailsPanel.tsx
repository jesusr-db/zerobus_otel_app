import { LogEntry, SeverityLevel } from '../types/logs';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { X, Copy, Check, ExternalLink } from 'lucide-react';
import { useState } from 'react';
import { JsonAttributesViewer } from './JsonAttributesViewer';

interface LogDetailsPanelProps {
  log: LogEntry;
  onClose: () => void;
  onViewTrace?: (traceId: string) => void;
}

export function LogDetailsPanel({ log, onClose, onViewTrace }: LogDetailsPanelProps) {
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // Severity colors
  const getSeverityColor = (severity: SeverityLevel | string) => {
    switch (severity) {
      case 'ERROR':
        return 'hsl(0, 84%, 60%)';
      case 'WARN':
        return 'hsl(30, 80%, 55%)';
      case 'INFO':
        return 'hsl(160, 60%, 45%)';
      case 'DEBUG':
        return 'hsl(var(--muted-foreground))';
      default:
        return 'hsl(var(--muted-foreground))';
    }
  };

  const severityColor = getSeverityColor(log.severity_text);

  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  };

  // Copy to clipboard
  const handleCopy = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  return (
    <div className="h-full flex flex-col bg-card border-l border-border">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <h2 className="text-lg font-semibold text-foreground">Log Details</h2>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* Metadata Section */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-foreground">Metadata</h3>

          <div className="space-y-2 text-sm">
            {/* Timestamp */}
            <div className="flex items-start justify-between">
              <span className="text-muted-foreground w-32 flex-shrink-0">Timestamp:</span>
              <span className="text-foreground font-mono flex-1 text-right">
                {formatTimestamp(log.log_timestamp)}
              </span>
            </div>

            {/* Service */}
            <div className="flex items-start justify-between">
              <span className="text-muted-foreground w-32 flex-shrink-0">Service:</span>
              <span className="text-foreground flex-1 text-right">{log.service_name}</span>
            </div>

            {/* Severity */}
            <div className="flex items-start justify-between">
              <span className="text-muted-foreground w-32 flex-shrink-0">Severity:</span>
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
            </div>

            {/* Trace ID */}
            {log.trace_id && log.trace_id !== '' && (
              <div className="flex items-start justify-between gap-2">
                <span className="text-muted-foreground w-32 flex-shrink-0">Trace ID:</span>
                <div className="flex items-center gap-2 flex-1 justify-end">
                  <span className="text-foreground font-mono text-xs truncate max-w-xs">
                    {log.trace_id}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2"
                    onClick={() => handleCopy(log.trace_id, 'trace_id')}
                  >
                    {copiedField === 'trace_id' ? (
                      <Check className="h-3 w-3" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                  {onViewTrace && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2"
                      onClick={() => onViewTrace(log.trace_id)}
                    >
                      <ExternalLink className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </div>
            )}

            {/* Span ID */}
            {log.span_id && log.span_id !== '' && (
              <div className="flex items-start justify-between gap-2">
                <span className="text-muted-foreground w-32 flex-shrink-0">Span ID:</span>
                <div className="flex items-center gap-2 flex-1 justify-end">
                  <span className="text-foreground font-mono text-xs truncate max-w-xs">
                    {log.span_id}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2"
                    onClick={() => handleCopy(log.span_id, 'span_id')}
                  >
                    {copiedField === 'span_id' ? (
                      <Check className="h-3 w-3" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Event Name */}
            {log.event_name && log.event_name !== '' && (
              <div className="flex items-start justify-between">
                <span className="text-muted-foreground w-32 flex-shrink-0">Event:</span>
                <span className="text-foreground flex-1 text-right">{log.event_name}</span>
              </div>
            )}
          </div>
        </div>

        {/* Body Section */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Message</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleCopy(log.body, 'body')}
              className="h-8"
            >
              {copiedField === 'body' ? (
                <>
                  <Check className="h-3 w-3 mr-1" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3 mr-1" />
                  Copy
                </>
              )}
            </Button>
          </div>
          <div className="rounded-md border border-border bg-muted/30 p-3">
            <pre className="text-sm text-foreground font-mono whitespace-pre-wrap break-words">
              {log.body}
            </pre>
          </div>
        </div>

        {/* Attributes Section */}
        <JsonAttributesViewer data={log.attributes} />
      </div>
    </div>
  );
}
