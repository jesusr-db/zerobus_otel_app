interface TimeRangeSelectorProps {
  value: '1h' | '24h';
  onChange: (value: '1h' | '24h') => void;
}

export function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  const options = [
    { value: '1h' as const, label: '1 hour' },
    { value: '24h' as const, label: '24 hours' },
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
