interface TimeRangeSelectorProps {
  value: '1h' | '24h' | '1M';
  onChange: (value: '1h' | '24h' | '1M') => void;
}

export function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  const options = [
    { value: '1h' as const, label: '1h' },
    { value: '24h' as const, label: '1d' },
    { value: '1M' as const, label: '1M' },
  ];

  return (
    <div className="flex gap-2">
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            value === option.value
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
