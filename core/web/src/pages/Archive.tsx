import { useState, useEffect, useMemo, useRef } from "react";
import { vertical } from "@/config/verticals";
import { Layout } from "@/components/Layout";
import { NewsCard } from "@/components/NewsCard";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fetchNewsData, NewsItem, formatFeedTypeLabel, searchItems } from "@/data/newsData";
import { fetchArchiveData } from "@/data/archiveData";
import { useSearch } from "@/contexts/SearchContext";
import { Helmet } from "react-helmet-async";
import { format } from "date-fns";
import { Archive as ArchiveIcon, Calendar, ChevronDown, ChevronUp } from "lucide-react";

interface MonthGroup {
  month: string;
  year: number;
  items: NewsItem[];
}

export default function Archive() {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([]);
  const [feedTypes, setFeedTypes] = useState<string[]>(["news"]);
  const [selectedFeedType, setSelectedFeedType] = useState("news");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [expandedMonths, setExpandedMonths] = useState<Set<string>>(new Set());
  const fallbackNewsRef = useRef<NewsItem[]>([]);
  const { searchQuery, setSearchQuery } = useSearch();
  const trimmedQuery = searchQuery.trim();

  useEffect(() => {
    const preloadFeedTypes = async () => {
      try {
        const data = await fetchNewsData();
        fallbackNewsRef.current = data.items;
        const available = data.feedTypes?.length ? data.feedTypes : ["news"];
        setFeedTypes(available);
        setSelectedFeedType((prev) =>
          available.includes(prev) ? prev : available[0]
        );
      } catch (err) {
        console.warn("Failed to preload feed types", err);
      }
    };
    preloadFeedTypes();
  }, []);

  const ensureFallbackItems = async (): Promise<NewsItem[]> => {
    if (fallbackNewsRef.current.length === 0) {
      try {
        const data = await fetchNewsData();
        fallbackNewsRef.current = data.items;
        if (data.feedTypes?.length) {
          setFeedTypes((prev) => (prev.length ? prev : data.feedTypes!));
        }
      } catch (err) {
        console.warn("Failed to fetch fallback news data", err);
      }
    }
    return fallbackNewsRef.current;
  };

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const archiveItems = await fetchArchiveData(selectedFeedType);
        if (archiveItems.length > 0) {
          setNewsItems(archiveItems);
          setExpandedMonths(new Set());
          setWarning(null);
          setError(null);
        } else {
          const fallback = await ensureFallbackItems();
          const filtered = fallback.filter(
            (item) => (item.feedType ?? "news") === selectedFeedType
          );
          setNewsItems(filtered);
          setExpandedMonths(new Set());
          setWarning("Archive files unavailable; showing recent cache instead.");
          setError(null);
        }
      } catch (err) {
        console.error("Failed to load archive data:", err);
        const fallback = await ensureFallbackItems();
        if (fallback.length) {
          const filtered = fallback.filter(
            (item) => (item.feedType ?? "news") === selectedFeedType
          );
          setNewsItems(filtered);
          setExpandedMonths(new Set());
          setWarning("Archive unavailable; showing recent cache instead.");
          setError(null);
        } else {
          setError("Failed to load archive data. Please try again later.");
        }
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [selectedFeedType]);

  const visibleItems = useMemo(
    () => searchItems(newsItems, trimmedQuery),
    [newsItems, trimmedQuery],
  );

  // Group news by month
  const monthlyGroups = useMemo(() => {
    const groups: Record<string, MonthGroup> = {};

    visibleItems.forEach((item) => {
      const monthKey = format(item.date, "yyyy-MM");
      const monthLabel = format(item.date, "MMMM yyyy");
      const year = item.date.getFullYear();

      if (!groups[monthKey]) {
        groups[monthKey] = {
          month: monthLabel,
          year,
          items: [],
        };
      }

      groups[monthKey].items.push(item);
    });

    // Sort by date descending (newest first)
    return Object.entries(groups)
      .sort((a, b) => b[0].localeCompare(a[0]))
      .map(([key, group]) => ({
        key,
        ...group,
      }));
  }, [visibleItems]);

  // Under a search, open every month that has a match so the reader doesn't
  // have to guess which one to click.
  useEffect(() => {
    setExpandedMonths(trimmedQuery ? new Set(monthlyGroups.map((g) => g.key)) : new Set());
  }, [trimmedQuery, monthlyGroups]);

  // Months between the oldest and newest with nothing collected. Say so
  // rather than let the reader wonder whether they scrolled past them.
  const gaps = useMemo(() => {
    const present = new Set(
      Array.from(new Set(newsItems.map((item) => format(item.date, "yyyy-MM")))),
    );
    const keys = Array.from(present).sort();
    if (keys.length < 2) return [];
    const ranges: string[] = [];
    const [firstY, firstM] = keys[0].split("-").map(Number);
    const [lastY, lastM] = keys[keys.length - 1].split("-").map(Number);
    let cursor = new Date(firstY, firstM - 1, 1);
    const end = new Date(lastY, lastM - 1, 1);
    let start: Date | null = null;
    while (cursor <= end) {
      const key = format(cursor, "yyyy-MM");
      if (!present.has(key)) {
        if (!start) start = cursor;
      } else if (start) {
        const prev = new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1);
        ranges.push(
          start.getTime() === prev.getTime()
            ? format(start, "MMMM yyyy")
            : `${format(start, "MMMM yyyy")} – ${format(prev, "MMMM yyyy")}`,
        );
        start = null;
      }
      cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
    }
    return ranges;
  }, [newsItems]);

  const toggleMonth = (key: string) => {
    const newExpanded = new Set(expandedMonths);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedMonths(newExpanded);
  };

  const expandAll = () => {
    setExpandedMonths(new Set(monthlyGroups.map((g) => g.key)));
  };

  const collapseAll = () => {
    setExpandedMonths(new Set());
  };

  const totalItems = newsItems.length;
  const feedTypeLabel = formatFeedTypeLabel(selectedFeedType);
  const oldest = monthlyGroups[monthlyGroups.length - 1];
  const newest = monthlyGroups[0];

  return (
    <Layout>
      <Helmet>
        <title>{`${feedTypeLabel} Archive — ${vertical.metaTitle}`}</title>
        <meta
          name="description"
          content={`Browse historical ${feedTypeLabel.toLowerCase()} organized by month.`}
        />
      </Helmet>

      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <ArchiveIcon className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-3xl font-bold text-foreground">
                  {feedTypeLabel} Archive
                </h1>
                <p className="text-[15px] text-muted-foreground mt-1">
                  Every story we've collected, by month. Use the search box to look for something specific.
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {feedTypes.map((type) => (
              <Button
                key={type}
                variant={selectedFeedType === type ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedFeedType(type)}
                className="text-[13px]"
              >
                {formatFeedTypeLabel(type)}
              </Button>
            ))}
          </div>

          {!loading && !error && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={expandAll}
                className="text-[13px]"
              >
                <ChevronDown className="h-4 w-4 mr-1" />
                Expand All
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={collapseAll}
                className="text-[13px]"
              >
                <ChevronUp className="h-4 w-4 mr-1" />
                Collapse All
              </Button>
            </div>
          )}
        </div>

        {warning && !error && (
          <Card className="p-4 bg-warning/10 border border-warning/30 text-warning text-[14px] font-mono">
            {warning}
          </Card>
        )}

        {loading ? (
          <div className="text-center py-12 bg-card rounded-lg border border-border">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent mb-4"></div>
            <p className="text-[15px] text-muted-foreground font-mono">
              Loading archive...
            </p>
          </div>
        ) : error ? (
          <div className="text-center py-12 bg-card rounded-lg border border-destructive">
            <p className="text-[15px] text-destructive font-mono">{error}</p>
          </div>
        ) : (
          <>
            {/* Summary */}
            <div className="text-[15px] text-foreground space-y-1">
              {trimmedQuery ? (
                <p>
                  <span className="font-medium">{visibleItems.length}</span>{" "}
                  {visibleItems.length === 1 ? "story mentions" : "stories mention"}{" "}
                  <span className="font-medium">“{trimmedQuery}”</span>
                  <span className="text-muted-foreground"> across {totalItems.toLocaleString()} archived {feedTypeLabel.toLowerCase()}</span>
                  {" "}
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    className="text-primary hover:underline"
                  >
                    Clear search
                  </button>
                </p>
              ) : (
                <p>
                  <span className="font-medium">{totalItems.toLocaleString()}</span>
                  <span className="text-muted-foreground">
                    {" "}archived {feedTypeLabel.toLowerCase()}
                    {oldest && newest && (
                      <> · {oldest.month === newest.month ? oldest.month : `${oldest.month} – ${newest.month}`}</>
                    )}
                  </span>
                </p>
              )}
              {gaps.length > 0 && (
                <p className="text-[13px] text-muted-foreground">
                  Nothing was collected for {gaps.join(", ")}.
                </p>
              )}
            </div>

            {trimmedQuery && monthlyGroups.length === 0 && (
              <Card className="p-8 text-center bg-card border-border">
                <p className="text-[15px] text-foreground">
                  No archived {feedTypeLabel.toLowerCase()} mention “{trimmedQuery}”.
                </p>
                <Button variant="outline" size="sm" className="mt-4" onClick={() => setSearchQuery("")}>
                  Clear search
                </Button>
              </Card>
            )}

            {/* Monthly Groups */}
            <div className="space-y-4">
              {monthlyGroups.map((group) => {
                const isExpanded = expandedMonths.has(group.key);

                return (
                  <Card key={group.key} className="overflow-hidden bg-card border-border">
                    <button
                      onClick={() => toggleMonth(group.key)}
                      className="w-full p-5 flex items-center justify-between hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <Calendar className="h-5 w-5 text-primary" />
                        <div className="text-left">
                          <h2 className="text-xl font-semibold text-foreground">
                            {group.month}
                          </h2>
                          <p className="text-[13px] text-muted-foreground font-mono">
                            {group.items.length} articles
                          </p>
                        </div>
                      </div>
                      {isExpanded ? (
                        <ChevronUp className="h-5 w-5 text-muted-foreground" />
                      ) : (
                        <ChevronDown className="h-5 w-5 text-muted-foreground" />
                      )}
                    </button>

                    {isExpanded && (
                      <div className="border-t border-border p-5 space-y-4">
                        {group.items.map((item, index) => (
                          <NewsCard key={item.id} item={item} index={index} highlight={trimmedQuery} />
                        ))}
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
