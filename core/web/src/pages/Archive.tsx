import { useState, useEffect, useMemo, useRef } from "react";
import { vertical } from "@/config/verticals";
import { Layout } from "@/components/Layout";
import { NewsCard } from "@/components/NewsCard";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fetchNewsData, NewsItem, formatFeedTypeLabel } from "@/data/newsData";
import { fetchArchiveData } from "@/data/archiveData";
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

  // Group news by month
  const monthlyGroups = useMemo(() => {
    const groups: Record<string, MonthGroup> = {};

    newsItems.forEach((item) => {
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
  const totalMonths = monthlyGroups.length;
  const feedTypeLabel = formatFeedTypeLabel(selectedFeedType);

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
                  Browse historical security {feedTypeLabel.toLowerCase()}
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
            {/* Stats */}
            <Card className="p-5 bg-card border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-8">
                  <div>
                    <p className="text-[13px] text-muted-foreground font-mono uppercase mb-1">
                      Total Articles
                    </p>
                    <p className="text-2xl font-bold text-foreground">{totalItems}</p>
                  </div>
                  <div>
                    <p className="text-[13px] text-muted-foreground font-mono uppercase mb-1">
                      Months Covered
                    </p>
                    <p className="text-2xl font-bold text-foreground">{totalMonths}</p>
                  </div>
                </div>
              </div>
            </Card>

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
                          <NewsCard key={item.id} item={item} index={index} />
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
