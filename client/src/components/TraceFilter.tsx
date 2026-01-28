import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { X, Link2 } from "lucide-react";

interface TraceFilterProps {
  traceId: string;
  onChange: (value: string) => void;
  onClear: () => void;
}

export function TraceFilter({ traceId, onChange, onClear }: TraceFilterProps) {
  // Basic trace ID format validation (typically hexadecimal, 16 or 32 chars)
  const isValidFormat = (value: string): boolean => {
    if (!value) return true; // Empty is valid
    // Check if it's hexadecimal and reasonable length
    return /^[a-fA-F0-9]{8,64}$/.test(value);
  };

  const hasInvalidFormat = traceId && !isValidFormat(traceId);

  return (
    <div className="relative w-80">
      <Link2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="text"
        placeholder="Filter by trace ID..."
        value={traceId}
        onChange={(e) => onChange(e.target.value)}
        className={`pl-10 pr-10 ${hasInvalidFormat ? "border-destructive" : ""}`}
      />
      {traceId && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          onClick={onClear}
        >
          <X className="h-4 w-4" />
        </Button>
      )}
      {hasInvalidFormat && (
        <div className="absolute -bottom-5 left-0 text-xs text-destructive">
          Invalid format (expected 8-64 hex characters)
        </div>
      )}
    </div>
  );
}
