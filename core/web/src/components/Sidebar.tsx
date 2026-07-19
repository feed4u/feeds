import { Button } from "@/components/ui/button";
import { NewsItem, getCategoryLabel, formatFeedTypeLabel } from "@/data/newsData";
import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

interface SidebarProps {
  feedTypes: string[];
  feedTypeCounts: Record<string, number>;
  selectedFeedType: string;
  onFeedTypeChange: (type: string) => void;
  selectedCategory: string;
  selectedSmartGroup: string;
  onCategoryChange: (category: string) => void;
  onSmartGroupChange: (group: string) => void;
  newsItems: NewsItem[];
}

export function Sidebar({
  feedTypes,
  feedTypeCounts,
  selectedFeedType,
  onFeedTypeChange,
  selectedCategory,
  selectedSmartGroup,
  onCategoryChange,
  onSmartGroupChange,
  newsItems,
}: SidebarProps) {
  const [categoriesOpen, setCategoriesOpen] = useState(false);
  const [smartGroupsOpen, setSmartGroupsOpen] = useState(false);
  const [feedTypesOpen, setFeedTypesOpen] = useState(false);

  // Dynamically generate categories from news items
  const categories = useMemo(() => {
    const categoryCounts: Record<string, number> = {};
    let curatedCount = 0;

    newsItems.forEach((item) => {
      if (item.curated) curatedCount++;
      const cat = item.category;
      categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
    });

    const cats = [
      { id: 'all', label: 'All', count: newsItems.length },
      { id: 'curated', label: 'Curated', count: curatedCount },
    ];

    // Sort by count descending
    const sortedCategories = Object.entries(categoryCounts)
      .map(([id, count]) => ({ id, label: getCategoryLabel(id), count }))
      .sort((a, b) => {
        if (b.count !== a.count) return b.count - a.count;
        return a.label.localeCompare(b.label);
      });

    return [...cats, ...sortedCategories];
  }, [newsItems]);

  // Sort feed types by count (desc)
  const sortedFeedTypes = useMemo(() => {
    return [...feedTypes].sort((a, b) => {
      const cb = feedTypeCounts[b] ?? 0;
      const ca = feedTypeCounts[a] ?? 0;
      if (cb !== ca) return cb - ca;
      return formatFeedTypeLabel(a).localeCompare(formatFeedTypeLabel(b));
    });
  }, [feedTypes, feedTypeCounts]);

  // Dynamically generate smart groups from news items
  const smartGroups = useMemo(() => {
    const groupCounts: Record<string, number> = {};

    newsItems.forEach((item) => {
      item.smartGroups.forEach((group) => {
        groupCounts[group] = (groupCounts[group] || 0) + 1;
      });
    });

    // Sort by count descending and take top 20
    return Object.entries(groupCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([id, count]) => ({
        id,
        label: id, // Use the group name as-is
        count,
      }));
  }, [newsItems]);

  return (
    <aside className="w-full lg:w-72 shrink-0 space-y-6">
      <section className="bg-card rounded-lg border border-border">
        <button
          onClick={() => setFeedTypesOpen(!feedTypesOpen)}
          className="w-full p-5 flex items-center justify-between lg:cursor-default"
        >
          <h2 className="text-[15px] font-semibold text-foreground uppercase tracking-wider font-mono">
            Feed Types
          </h2>
          <span className="lg:hidden">
            {feedTypesOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </span>
        </button>
        <div className={`px-5 pb-5 ${feedTypesOpen ? 'block' : 'hidden'} lg:block`}>
          <div className="flex flex-wrap gap-2">
            {sortedFeedTypes.map((type) => (
              <Button
                key={type}
                variant={selectedFeedType === type ? "pillActive" : "pill"}
                size="pill"
                onClick={() => onFeedTypeChange(type)}
                className="animate-fade-in"
              >
                {formatFeedTypeLabel(type)}
                <span className="text-muted-foreground ml-1">
                  ({feedTypeCounts[type] ?? 0})
                </span>
              </Button>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-card rounded-lg border border-border">
        <button
          onClick={() => setCategoriesOpen(!categoriesOpen)}
          className="w-full p-5 flex items-center justify-between lg:cursor-default"
        >
          <h2 className="text-[15px] font-semibold text-foreground uppercase tracking-wider font-mono">
            Categories
          </h2>
          <span className="lg:hidden">
            {categoriesOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </span>
        </button>
        <div className={`px-5 pb-5 ${categoriesOpen ? 'block' : 'hidden'} lg:block`}>
          <div className="space-y-2">
            {categories.map((cat, idx) => (
              <button
                key={cat.id}
                onClick={() => {
                  onCategoryChange(cat.id);
                  onSmartGroupChange('');
                }}
                className={`w-full grid grid-cols-[1fr_auto] items-start gap-3 p-3 rounded-lg border transition-colors ${
                  selectedCategory === cat.id
                    ? 'border-primary/50 bg-primary/10 text-primary'
                    : 'border-border bg-background hover:bg-muted'
                } animate-fade-in`}
                style={{ animationDelay: `${idx * 30}ms` }}
              >
                <span className="text-sm font-medium leading-tight line-clamp-2 text-left">{cat.label}</span>
                <span className="text-sm font-mono text-muted-foreground tabular-nums text-right">{cat.count}</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-card rounded-lg border border-border">
        <button
          onClick={() => setSmartGroupsOpen(!smartGroupsOpen)}
          className="w-full p-5 flex items-center justify-between lg:cursor-default"
        >
          <h2 className="text-[15px] font-semibold text-foreground uppercase tracking-wider font-mono">
            Smart Groups
          </h2>
          <span className="lg:hidden">
            {smartGroupsOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </span>
        </button>
        <div className={`px-5 pb-5 ${smartGroupsOpen ? 'block' : 'hidden'} lg:block`}>
          <div className="space-y-2">
            {smartGroups.map((group, idx) => (
              <button
                key={group.id}
                onClick={() => {
                  onSmartGroupChange(group.id);
                  onCategoryChange('all');
                }}
                className={`w-full grid grid-cols-[1fr_auto] items-start gap-3 p-3 rounded-lg border transition-colors ${
                  selectedSmartGroup === group.id
                    ? 'border-primary/50 bg-primary/10 text-primary'
                    : 'border-border bg-background hover:bg-muted'
                } animate-fade-in`}
                style={{ animationDelay: `${idx * 30}ms` }}
              >
                <span className="text-sm font-medium leading-tight line-clamp-2 text-left">{group.label}</span>
                <span className="text-sm font-mono text-muted-foreground tabular-nums text-right">{group.count}</span>
              </button>
            ))}
          </div>
        </div>
      </section>
    </aside>
  );
}
