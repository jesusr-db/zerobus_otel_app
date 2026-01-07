import { SeverityLevel } from '../types/logs';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { X } from 'lucide-react';

interface SeverityFilterProps {
  selectedSeverities: SeverityLevel[];
  severityCounts: Record<string, number>;
  onToggleSeverity: (severity: SeverityLevel) => void;
  onClearAll: () => void;
}

const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  ERROR: 'hsl(0, 84%, 60%)',
  WARN: 'hsl(30, 80%, 55%)',
  INFO: 'hsl(160, 60%, 45%)',
  DEBUG: 'hsl(var(--muted-foreground))',
  FATAL: 'hsl(0, 100%, 40%)',
};

const ALL_SEVERITIES: SeverityLevel[] = ['ERROR', 'WARN', 'INFO', 'DEBUG'];

export function SeverityFilter({
  selectedSeverities,
  severityCounts,
  onToggleSeverity,
  onClearAll,
}: SeverityFilterProps) {
  const getSeverityColor = (severity: SeverityLevel) => {
    return SEVERITY_COLORS[severity] || SEVERITY_COLORS.DEBUG;
  };

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-medium text-muted-foreground">Severity:</span>

      <div className="flex gap-2">
        {ALL_SEVERITIES.map((severity) => {
          const isSelected = selectedSeverities.includes(severity);
          const count = severityCounts[severity] || 0;
          const color = getSeverityColor(severity);

          return (
            <Badge
              key={severity}
              variant={isSelected ? 'default' : 'outline'}
              className="cursor-pointer transition-all hover:scale-105"
              style={{
                backgroundColor: isSelected ? color : 'transparent',
                borderColor: color,
                color: isSelected ? 'white' : color,
                borderWidth: '2px',
              }}
              onClick={() => onToggleSeverity(severity)}
            >
              {severity}
              <span className="ml-1.5 font-semibold">
                ({count.toLocaleString()})
              </span>
            </Badge>
          );
        })}
      </div>

      {selectedSeverities.length > 0 && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onClearAll}
          className="h-8 px-2 text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4 mr-1" />
          Clear
        </Button>
      )}
    </div>
  );
}
