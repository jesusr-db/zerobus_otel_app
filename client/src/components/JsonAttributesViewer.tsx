import { JsonView, allExpanded, defaultStyles } from "react-json-view-lite";
import "react-json-view-lite/dist/index.css";
import { Button } from "./ui/button";
import { Copy, Check } from "lucide-react";
import { useState } from "react";

interface JsonAttributesViewerProps {
  data: Record<string, any>;
}

export function JsonAttributesViewer({ data }: JsonAttributesViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Attributes</h3>
        <Button variant="ghost" size="sm" onClick={handleCopy} className="h-8">
          {copied ? (
            <>
              <Check className="h-3 w-3 mr-1" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-3 w-3 mr-1" />
              Copy JSON
            </>
          )}
        </Button>
      </div>

      <div className="rounded-md border border-border bg-muted/30 p-3 max-h-96 overflow-auto">
        {Object.keys(data).length === 0 ? (
          <div className="text-sm text-muted-foreground italic">
            No attributes
          </div>
        ) : (
          <div className="text-foreground">
            <JsonView
              data={data}
              shouldExpandNode={allExpanded}
              style={{
                ...defaultStyles,
                container: "font-mono text-xs text-foreground",
                basicChildStyle: "padding-left: 1rem",
                label: "color: white; font-weight: 500",
                nullValue: "color: #94a3b8",
                undefinedValue: "color: #94a3b8",
                booleanValue: "color: #60a5fa",
                numberValue: "color: #34d399",
                stringValue: "color: #fbbf24",
                punctuation: "color: white",
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
