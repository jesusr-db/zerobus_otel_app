import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { TimeRange } from '../types/observability';

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (value: TimeRange) => void;
}

export function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  const options: Array<{ value: TimeRange; label: string }> = [
    { value: '5m', label: '5 minutes' },
    { value: '1h', label: '1 hour' },
    { value: '1d', label: '1 day' },
    { value: '1w', label: '1 week' },
  ];

  return (
    <div className="flex items-center gap-3">
      <label className="text-sm font-semibold text-foreground">
        Timeframe:
      </label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-[180px] bg-primary text-primary-foreground border-primary hover:bg-primary/90 focus:ring-primary">
          <SelectValue placeholder="Select time range" />
        </SelectTrigger>
        <SelectContent className="bg-popover">
          {options.map((option) => (
            <SelectItem
              key={option.value}
              value={option.value}
              className="hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground"
            >
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
