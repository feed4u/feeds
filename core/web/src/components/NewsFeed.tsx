import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { Layout } from "./Layout";
import { Sidebar } from "./Sidebar";
import { NewsCard } from "./NewsCard";
import { FilterBar } from "./FilterBar";
import { fetchNewsChunk, NewsItem, formatFeedTypeLabel } from "@/data/newsData";
import { Button } from "@/components/ui/button";
import { useSearch } from "@/contexts/SearchContext";

export function NewsFeed() {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([]);
  const [feedTypes, setFeedTypes] = useState<string[]>(["news"]);
  const [selectedFeedType, setSelectedFeedType] = useState("news");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedSmartGroup, setSelectedSmartGroup] = useState("");
  const { searchQuery } = useSearch();
  const [nextChunk, setNextChunk] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const seenUrlsRef = useRef<Set<string>>(new Set());
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setSelectedCategory("all");
    setSelectedSmartGroup("");
  }, [selectedFeedType]);

  // Initial chunk load
  useEffect(() => {
    let cancelled = false;
    async function loadInitial() {
      try {
        setLoading(true);
        const page = await fetchNewsChunk();
        if (cancelled) return;
        // dedupe while adding
        const seen = seenUrlsRef.current;
        const unique = page.items.filter((it) => {
          if (seen.has(it.url)) return false;
          seen.add(it.url);
          return true;
        });
        setNewsItems(unique);
        const available = page.feedTypes?.length ? page.feedTypes : ["news"];
        setFeedTypes(available);
        setSelectedFeedType((prev) => (available.includes(prev) ? prev : available[0]));
        setNextChunk(page.nextChunk);
        setError(null);
      } catch (err) {
        console.error("Failed to load news data:", err);
        setError("Failed to load news feed. Please try again later.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadInitial();
    return () => {
      cancelled = true;
    };
  }, []);

  const loadMore = useCallback(async () => {
    if (!nextChunk || loadingMore) return;
    try {
      setLoadingMore(true);
      const page = await fetchNewsChunk(nextChunk);
      const seen = seenUrlsRef.current;
      const unique = page.items.filter((it) => {
        if (seen.has(it.url)) return false;
        seen.add(it.url);
        return true;
      });
      setNewsItems((prev) => [...prev, ...unique]);
      setNextChunk(page.nextChunk);
    } catch (err) {
      console.error("Failed to load more:", err);
    } finally {
      setLoadingMore(false);
    }
  }, [nextChunk, loadingMore]);

  // Observe sentinel for infinite scroll
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        const [e] = entries;
        if (e.isIntersecting) {
          loadMore();
        }
      },
      { rootMargin: "1200px 0px" }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [loadMore]);

  const feedTypeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    newsItems.forEach((item) => {
      const key = item.feedType || "news";
      counts[key] = (counts[key] || 0) + 1;
    });
    return counts;
  }, [newsItems]);

  const feedTypeItems = useMemo(() => {
    return newsItems.filter((item) => item.feedType === selectedFeedType);
  }, [newsItems, selectedFeedType]);

  const filteredNews = useMemo(() => {
    let items = [...feedTypeItems];

    // Filter by category
    if (selectedCategory === "curated") {
      items = items.filter((item) => item.curated);
    } else if (selectedCategory !== "all") {
      items = items.filter((item) => item.category === selectedCategory);
    }

    // Filter by smart group
    if (selectedSmartGroup) {
      items = items.filter((item) =>
        item.smartGroups.includes(selectedSmartGroup)
      );
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      items = items.filter(
        (item) =>
          item.title.toLowerCase().includes(query) ||
          item.summary.toLowerCase().includes(query) ||
          item.source.toLowerCase().includes(query)
      );
    }

    // Sort by latest by default
    items.sort((a, b) => b.date.getTime() - a.date.getTime());

    return items;
  }, [feedTypeItems, selectedCategory, selectedSmartGroup, searchQuery]);

  return (
    <Layout>
      <div className="flex flex-col lg:flex-row gap-6">
          <Sidebar
            feedTypes={feedTypes}
            feedTypeCounts={feedTypeCounts}
            selectedFeedType={selectedFeedType}
            onFeedTypeChange={setSelectedFeedType}
            selectedCategory={selectedCategory}
            selectedSmartGroup={selectedSmartGroup}
            onCategoryChange={setSelectedCategory}
            onSmartGroupChange={setSelectedSmartGroup}
            newsItems={feedTypeItems}
          />

          <div className="flex-1 min-w-0">
            <FilterBar
              totalItems={feedTypeItems.length}
              filteredItems={filteredNews.length}
              feedTypeLabel={formatFeedTypeLabel(selectedFeedType)}
            />

            <div className="space-y-4">
              {loading ? (
                <div className="text-center py-12 bg-card rounded-lg border border-border">
                  <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent mb-4"></div>
                  <p className="text-[15px] text-muted-foreground font-mono">
                    Loading news feed...
                  </p>
                </div>
              ) : error ? (
                <div className="text-center py-12 bg-card rounded-lg border border-destructive">
                  <p className="text-[15px] text-destructive font-mono">
                    {error}
                  </p>
                </div>
              ) : filteredNews.length === 0 ? (
                <div className="text-center py-12 bg-card rounded-lg border border-border">
                  <p className="text-[15px] text-muted-foreground font-mono">
                    No articles found matching your criteria.
                  </p>
                </div>
              ) : (
                filteredNews.map((item, index) => (
                  <NewsCard
                    key={item.id}
                    item={item}
                    index={index}
                    selectedCategory={selectedCategory}
                    selectedSmartGroup={selectedSmartGroup}
                    onCategoryClick={(category) => {
                      setSelectedCategory(category);
                      setSelectedSmartGroup('');
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    onSmartGroupClick={(group) => {
                      setSelectedSmartGroup(group);
                      setSelectedCategory('all');
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                  />
                ))
              )}
              {/* Infinite scroll sentinel */}
              {!loading && !error && (
                <div className="py-6 text-center">
                  {nextChunk && (
                    <>
                      <div ref={sentinelRef} className="mb-3">
                        <span className="text-[13px] font-mono text-muted-foreground">
                          {loadingMore ? 'Loading more…' : 'Scroll to load more'}
                        </span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={loadMore}
                        disabled={loadingMore}
                        className="font-mono text-[13px]"
                      >
                        {loadingMore ? 'Loading…' : 'Load more'}
                      </Button>
                    </>
                  )}
                  {!nextChunk && (
                    <span className="text-[13px] font-mono text-muted-foreground">End of results</span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
    </Layout>
  );
}
