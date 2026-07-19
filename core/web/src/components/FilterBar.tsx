import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface FilterBarProps {
  totalItems: number;
  filteredItems: number;
  feedTypeLabel?: string;
}

export function FilterBar({ totalItems, filteredItems, feedTypeLabel }: FilterBarProps) {
  const [filtersOpen, setFiltersOpen] = useState(false);
  const label = feedTypeLabel ? feedTypeLabel : "headlines";

  return (
    <div className="space-y-4 mb-6">
      <div className="flex items-center justify-between text-[15px]">
        <div className="flex items-center gap-2">
          <span className="text-foreground font-medium">Latest {label}</span>
          <span className="text-muted-foreground font-mono">
            Showing {filteredItems} of {totalItems} items
          </span>
        </div>
        <span className="text-muted-foreground font-mono text-[13px]">
          Updated: {new Date().toLocaleString()}
        </span>
      </div>
    </div>
  );
}
