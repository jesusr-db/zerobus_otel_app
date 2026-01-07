import { Button } from './ui/button';
import { Input } from './ui/input';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';
import { Search, Filter, HelpCircle } from 'lucide-react';

interface SearchModeToggleProps {
  searchTerm: string;
  searchMode: 'simple' | 'advanced';
  onSearchChange: (value: string) => void;
  onModeToggle: () => void;
  disabled?: boolean;
}

export function SearchModeToggle({
  searchTerm,
  searchMode,
  onSearchChange,
  onModeToggle,
  disabled = false,
}: SearchModeToggleProps) {
  const placeholder =
    searchMode === 'simple'
      ? 'Search in body and attributes...'
      : 'Advanced: body:term severity:ERROR trace_id:abc123';

  return (
    <div className="flex gap-2 flex-1">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="text"
          placeholder={placeholder}
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-10 pr-10"
          disabled={disabled}
        />
        {searchMode === 'advanced' && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground cursor-help" />
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-md p-4">
                <div className="space-y-3">
                  <div className="font-semibold text-sm">Advanced Search Syntax</div>

                  <div className="space-y-2 text-xs">
                    <div>
                      <div className="font-medium text-foreground mb-1">Field-Specific Search:</div>
                      <div className="space-y-1 text-muted-foreground font-mono">
                        <div>body:database</div>
                        <div>severity:ERROR</div>
                        <div>trace_id:abc123</div>
                        <div>attributes.http.status_code:500</div>
                      </div>
                    </div>

                    <div>
                      <div className="font-medium text-foreground mb-1">Operators:</div>
                      <div className="space-y-1 text-muted-foreground">
                        <div><span className="font-mono">AND</span> - Combine conditions (default)</div>
                        <div><span className="font-mono">OR</span> - Match any condition</div>
                        <div><span className="font-mono">NOT</span> - Exclude matches</div>
                      </div>
                    </div>

                    <div>
                      <div className="font-medium text-foreground mb-1">Examples:</div>
                      <div className="space-y-1 text-muted-foreground font-mono text-[10px]">
                        <div>severity:ERROR AND body:connection</div>
                        <div>body:"timeout error"</div>
                        <div>attributes.http.method:POST</div>
                      </div>
                    </div>
                  </div>
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>

      <Button
        variant={searchMode === 'advanced' ? 'default' : 'outline'}
        size="default"
        onClick={onModeToggle}
        disabled={disabled}
        className="min-w-[120px]"
      >
        <Filter className="h-4 w-4 mr-2" />
        {searchMode === 'simple' ? 'Simple' : 'Advanced'}
      </Button>
    </div>
  );
}
