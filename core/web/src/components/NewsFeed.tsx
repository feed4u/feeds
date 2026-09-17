import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Layout } from "./Layout";
import { NewsCard } from "./NewsCard";
import { fetchNewsChunk, NewsItem, formatFeedTypeLabel, searchItems } from "@/data/newsData";
import { Button } from "@/components/ui/button";
import { useSearch } from "@/contexts/SearchContext";
import { vertical } from "@/config/verticals";
import { format, formatDistanceToNow, isToday, isYesterday } from "date-fns";
import { ChevronDown } from "lucide-react";

// ---------------------------------------------------------------------------
// Views: the one choice a reader makes before reading. "Headlines" is the
// default and excludes research sources, which get their own lane so a few
// hundred paper abstracts never bury the day's news.

const HEADLINES = "headlines";
const RESEARCH = "research";
const HAS_RESEARCH_LANE = vertical.researchSources.length > 0;

interface View {
  id: string;
  label: string;
  count: number;
}

function itemInView(item: NewsItem, view: string): boolean {
  if (view === RESEARCH) return item.isResearch;
  if (item.isResearch && HAS_RESEARCH_LANE) return false;
  if (view === HEADLINES) return item.feedType === "news";
  return item.feedType === view;
}

const MAX_TOPICS = 16;

// A run of this many consecutive stories from one source is folded into a
// single row so one bulk-posting feed can't dominate a day.
const BURST_MIN = 6;
const BURST_KEEP = 2;

type Row =
  | { kind: "item"; item: NewsItem; index: number }
  | { kind: "burst"; key: string; source: string; items: NewsItem[]; index: number };

function toRows(items: NewsItem[], expanded: Set<string>, dayKey: string): Row[] {
  const rows: Row[] = [];
  let i = 0;
  while (i < items.length) {
    let j = i;
    while (j < items.length && items[j].sourceName === items[i].sourceName) j++;
    const run = items.slice(i, j);
    const key = `${dayKey}:${items[i].sourceName}:${i}`;
    if (run.length >= BURST_MIN && !expanded.has(key)) {
      run.slice(0, BURST_KEEP).forEach((item, k) => rows.push({ kind: "item", item, index: i + k }));
      rows.push({ kind: "burst", key, source: items[i].sourceName, items: run.slice(BURST_KEEP), index: i + BURST_KEEP });
    } else {
      run.forEach((item, k) => rows.push({ kind: "item", item, index: i + k }));
    }
    i = j;
  }
  return rows;
}

function dayLabel(date: Date): string {
  if (isToday(date)) return "Today";
  if (isYesterday(date)) return "Yesterday";
  const sameYear = date.getFullYear() === new Date().getFullYear();
  return format(date, sameYear ? "EEEE d MMMM" : "EEEE d MMMM yyyy");
}

interface DayGroup {
  key: string;
  label: string;
  items: NewsItem[];
}

function groupByDay(items: NewsItem[]): DayGroup[] {
  const groups: DayGroup[] = [];
  for (const item of items) {
    const key = item.publishedTs ? format(item.date, "yyyy-MM-dd") : "undated";
    const last = groups[groups.length - 1];
    if (last && last.key === key) {
      last.items.push(item);
    } else {
      groups.push({ key, label: key === "undated" ? "Undated" : dayLabel(item.date), items: [item] });
    }
  }
  return groups;
}

export function NewsFeed() {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([]);
  const [generatedAt, setGeneratedAt] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nextChunk, setNextChunk] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [expandedBursts, setExpandedBursts] = useState<Set<string>>(new Set());
  const seenUrlsRef = useRef<Set<string>>(new Set());
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // View and topic live in the URL so a filtered feed can be bookmarked.
  const [params, setParams] = useSearchParams();
  const selectedView = params.get("view") || HEADLINES;
  const selectedTopic = params.get("topic") || "";
  const { searchQuery, setSearchQuery } = useSearch();

  const updateParams = useCallback(
    (changes: Record<string, string | null>) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [k, v] of Object.entries(changes)) {
            if (v) next.set(k, v);
            else next.delete(k);
          }
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const selectView = (view: string) =>
    updateParams({ view: view === HEADLINES ? null : view, topic: null });
  const selectTopic = (topic: string) =>
    updateParams({ topic: topic === selectedTopic ? null : topic });

  const addItems = useCallback((incoming: NewsItem[]) => {
    const seen = seenUrlsRef.current;
    const unique = incoming.filter((it) => {
      if (seen.has(it.url)) return false;
      seen.add(it.url);
      return true;
    });
    setNewsItems((prev) => [...prev, ...unique]);
  }, []);

  // Initial chunk load
  useEffect(() => {
    let cancelled = false;
    async function loadInitial() {
      try {
        setLoading(true);
        const page = await fetchNewsChunk();
        if (cancelled) return;
        addItems(page.items);
        setGeneratedAt(page.generatedAt);
        setNextChunk(page.nextChunk);
        setError(null);
      } catch (err) {
        console.error("Failed to load news data:", err);
        setError("Couldn't load the feed. Please try again in a moment.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadInitial();
    return () => {
      cancelled = true;
    };
  }, [addItems]);

  const loadMore = useCallback(async () => {
    if (!nextChunk || loadingMore) return;
    try {
      setLoadingMore(true);
      const page = await fetchNewsChunk(nextChunk);
      addItems(page.items);
      setNextChunk(page.nextChunk);
    } catch (err) {
      console.error("Failed to load more:", err);
    } finally {
      setLoadingMore(false);
    }
  }, [nextChunk, loadingMore, addItems]);

  // Infinite scroll — only while browsing, never under a search (a search
  // that keeps pulling older chunks while showing "no results" reads as broken).
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el || searchQuery) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) loadMore();
      },
      { rootMargin: "1200px 0px" },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [loadMore, searchQuery]);

  const views = useMemo<View[]>(() => {
    const counts: Record<string, number> = {};
    for (const item of newsItems) {
      const id = item.isResearch && HAS_RESEARCH_LANE ? RESEARCH : item.feedType === "news" ? HEADLINES : item.feedType;
      counts[id] = (counts[id] || 0) + 1;
    }
    const others = Object.keys(counts)
      .filter((id) => id !== HEADLINES && id !== RESEARCH)
      .sort((a, b) => counts[b] - counts[a] || a.localeCompare(b))
      .map((id) => ({ id, label: formatFeedTypeLabel(id), count: counts[id] }));
    const list: View[] = [{ id: HEADLINES, label: "Headlines", count: counts[HEADLINES] || 0 }];
    if (HAS_RESEARCH_LANE) list.push({ id: RESEARCH, label: "Research", count: counts[RESEARCH] || 0 });
    return [...list, ...others];
  }, [newsItems]);

  const viewItems = useMemo(
    () => newsItems.filter((item) => itemInView(item, selectedView)),
    [newsItems, selectedView],
  );

  const topics = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const item of viewItems) {
      for (const g of item.smartGroups) counts[g] = (counts[g] || 0) + 1;
    }
    const sorted = Object.entries(counts)
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, MAX_TOPICS)
      .map(([id, count]) => ({ id, count }));
    if (selectedTopic && counts[selectedTopic] && !sorted.some((t) => t.id === selectedTopic)) {
      sorted.push({ id: selectedTopic, count: counts[selectedTopic] });
    }
    return sorted;
  }, [viewItems, selectedTopic]);

  const topicItems = useMemo(() => {
    const items = selectedTopic
      ? viewItems.filter((item) => item.smartGroups.includes(selectedTopic))
      : [...viewItems];
    return items.sort((a, b) => b.date.getTime() - a.date.getTime());
  }, [viewItems, selectedTopic]);

  const results = useMemo(() => searchItems(topicItems, searchQuery), [topicItems, searchQuery]);
  const dayGroups = useMemo(() => (searchQuery ? [] : groupByDay(results)), [results, searchQuery]);

  // Matches in the lanes the reader is *not* looking at, so a search never
  // silently misses a story that only appears under Research or Blogs.
  const otherViewMatches = useMemo(() => {
    if (!searchQuery.trim()) return [];
    return views
      .filter((v) => v.id !== selectedView)
      .map((v) => ({
        view: v,
        count: searchItems(newsItems.filter((item) => itemInView(item, v.id)), searchQuery).length,
      }))
      .filter(({ count }) => count > 0);
  }, [views, selectedView, newsItems, searchQuery]);

  const viewLabel = views.find((v) => v.id === selectedView)?.label ?? "Stories";
  const archiveSearchHref = `/archive?q=${encodeURIComponent(searchQuery)}`;
  const trimmedQuery = searchQuery.trim();

  const expandBurst = (key: string) =>
    setExpandedBursts((prev) => new Set(prev).add(key));

  const renderRows = (rows: Row[]) =>
    rows.map((row) =>
      row.kind === "item" ? (
        <NewsCard
          key={row.item.id}
          item={row.item}
          index={row.index}
          selectedSmartGroup={selectedTopic}
          highlight={trimmedQuery}
          onSmartGroupClick={(group) => {
            selectTopic(group);
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        />
      ) : (
        <button
          key={row.key}
          type="button"
          onClick={() => expandBurst(row.key)}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-lg border border-dashed border-border text-[14px] text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
        >
          <ChevronDown className="h-4 w-4" />
          {row.items.length} more from {row.source}
        </button>
      ),
    );

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <p className="md:hidden mb-3 text-[13px] text-muted-foreground">{vertical.tagline}</p>

        {/* View selector */}
        <div className="flex flex-wrap items-center gap-2">
          {views.map((view) => (
            <Button
              key={view.id}
              variant={selectedView === view.id ? "pillActive" : "pill"}
              size="pill"
              onClick={() => selectView(view.id)}
              className="font-sans"
            >
              {view.label}
              {view.count > 0 && (
                <span className="text-muted-foreground ml-1.5 text-[12px]">{view.count}</span>
              )}
            </Button>
          ))}
        </div>

        {/* Topic chips: wrap on desktop, scroll sideways on phones */}
        {topics.length > 0 && (
          <div className="mt-3 -mx-4 px-4 md:mx-0 md:px-0 flex md:flex-wrap gap-1.5 overflow-x-auto md:overflow-visible pb-1 scrollbar-none">
            <button
              type="button"
              onClick={() => selectTopic("")}
              className={`shrink-0 text-[13px] px-2.5 py-1 rounded-full border transition-colors ${
                !selectedTopic
                  ? "border-primary/50 bg-primary/10 text-primary"
                  : "border-border text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              All topics
            </button>
            {topics.map((topic) => (
              <button
                key={topic.id}
                type="button"
                onClick={() => selectTopic(topic.id)}
                className={`shrink-0 text-[13px] px-2.5 py-1 rounded-full border transition-colors whitespace-nowrap ${
                  selectedTopic === topic.id
                    ? "border-primary/50 bg-primary/10 text-primary"
                    : "border-border text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                {topic.id}
                <span className="ml-1 text-[11px] opacity-70 tabular-nums">{topic.count}</span>
              </button>
            ))}
          </div>
        )}

        {/* Status line */}
        <div className="mt-4 mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-[14px]">
          {trimmedQuery ? (
            <span className="text-foreground">
              <span className="font-medium">{results.length}</span>{" "}
              {results.length === 1 ? "story mentions" : "stories mention"}{" "}
              <span className="font-medium">“{trimmedQuery}”</span>
              <span className="text-muted-foreground"> in recent {viewLabel.toLowerCase()}</span>
            </span>
          ) : (
            <span className="text-foreground">
              <span className="font-medium">{viewLabel}</span>
              {selectedTopic && <span className="text-muted-foreground"> · {selectedTopic}</span>}
              <span className="text-muted-foreground"> · {results.length} stories</span>
            </span>
          )}
          {generatedAt && (
            <span className="text-muted-foreground text-[13px]" title={generatedAt.toLocaleString()}>
              Updated {formatDistanceToNow(generatedAt, { addSuffix: true })}
            </span>
          )}
        </div>

        {otherViewMatches.length > 0 && (
          <p className="-mt-1 mb-3 text-[13px] text-muted-foreground">
            Also in{" "}
            {otherViewMatches.map(({ view, count }, i) => (
              <span key={view.id}>
                {i > 0 && " · "}
                <button
                  type="button"
                  onClick={() => updateParams({ view: view.id === HEADLINES ? null : view.id })}
                  className="text-primary hover:underline"
                >
                  {view.label} ({count})
                </button>
              </span>
            ))}
          </p>
        )}

        <div className="space-y-3">
          {loading ? (
            <div className="text-center py-12 bg-card rounded-lg border border-border">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent mb-4"></div>
              <p className="text-[15px] text-muted-foreground">Loading the latest stories…</p>
            </div>
          ) : error ? (
            <div className="text-center py-12 bg-card rounded-lg border border-destructive">
              <p className="text-[15px] text-destructive">{error}</p>
            </div>
          ) : results.length === 0 ? (
            <div className="text-center py-12 px-4 bg-card rounded-lg border border-border space-y-4">
              {trimmedQuery ? (
                <>
                  <p className="text-[15px] text-foreground">
                    No recent {viewLabel.toLowerCase()} mention “{trimmedQuery}”.
                  </p>
                  <div className="flex flex-wrap justify-center gap-2">
                    <Button asChild size="sm">
                      <Link to={archiveSearchHref}>Search the archive</Link>
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setSearchQuery("")}>
                      Clear search
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-[15px] text-foreground">
                    No recent {viewLabel.toLowerCase()}
                    {selectedTopic ? ` tagged “${selectedTopic}”` : ""}.
                  </p>
                  <div className="flex flex-wrap justify-center gap-2">
                    {selectedTopic && (
                      <Button variant="outline" size="sm" onClick={() => selectTopic("")}>
                        Show all topics
                      </Button>
                    )}
                    {selectedView !== HEADLINES && (
                      <Button variant="outline" size="sm" onClick={() => selectView(HEADLINES)}>
                        Back to headlines
                      </Button>
                    )}
                  </div>
                </>
              )}
            </div>
          ) : trimmedQuery ? (
            <>
              {renderRows(results.map((item, index) => ({ kind: "item", item, index })))}
              <div className="py-4 text-center text-[14px] text-muted-foreground">
                Looking for something older?{" "}
                <Link to={archiveSearchHref} className="text-primary hover:underline">
                  Search the archive
                </Link>
              </div>
            </>
          ) : (
            dayGroups.map((group) => (
              <section key={group.key} className="space-y-3">
                <h2 className="pt-3 text-[13px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {group.label}
                  <span className="ml-2 font-normal normal-case tracking-normal">{group.items.length}</span>
                </h2>
                {renderRows(
                  selectedView === RESEARCH
                    ? group.items.map((item, index) => ({ kind: "item" as const, item, index }))
                    : toRows(group.items, expandedBursts, group.key),
                )}
              </section>
            ))
          )}

          {/* Infinite scroll sentinel */}
          {!loading && !error && !trimmedQuery && (
            <div className="py-6 text-center">
              {nextChunk ? (
                <>
                  <div ref={sentinelRef} className="mb-3">
                    <span className="text-[13px] text-muted-foreground">
                      {loadingMore ? "Loading older stories…" : ""}
                    </span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={loadMore}
                    disabled={loadingMore}
                    className="text-[13px]"
                  >
                    {loadingMore ? "Loading…" : "Load older stories"}
                  </Button>
                </>
              ) : (
                <span className="text-[13px] text-muted-foreground">
                  You've reached the end of the recent stories.{" "}
                  <Link to="/archive" className="text-primary hover:underline">Browse the archive</Link>
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
