import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Layout } from "./Layout";
import { NewsCard } from "./NewsCard";
import { fetchNewsChunk, NewsItem, StoryTelling, formatFeedTypeLabel, searchItems } from "@/data/newsData";
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

/** Height of the sticky site header, published by <Header> as a CSS variable. */
function headerHeight(): number {
  const raw = getComputedStyle(document.documentElement).getPropertyValue("--app-header-h");
  const value = parseInt(raw, 10);
  return Number.isFinite(value) ? value : 64;
}

// A run of this many consecutive stories from one source is folded into a
// single row so one bulk-posting feed can't dominate a day.
const BURST_MIN = 6;
const BURST_KEEP = 2;

type Row =
  | { kind: "item"; entry: FeedEntry; index: number }
  | { kind: "burst"; key: string; source: string; entries: FeedEntry[]; index: number };

function toRows(entries: FeedEntry[], expanded: Set<string>, dayKey: string): Row[] {
  const rows: Row[] = [];
  let i = 0;
  while (i < entries.length) {
    let j = i;
    while (j < entries.length && entries[j].item.sourceName === entries[i].item.sourceName) j++;
    const run = entries.slice(i, j);
    const key = `${dayKey}:${entries[i].item.sourceName}:${i}`;
    if (run.length >= BURST_MIN && !expanded.has(key)) {
      run.slice(0, BURST_KEEP).forEach((entry, k) => rows.push({ kind: "item", entry, index: i + k }));
      rows.push({ kind: "burst", key, source: entries[i].item.sourceName, entries: run.slice(BURST_KEEP), index: i + BURST_KEEP });
    } else {
      run.forEach((entry, k) => rows.push({ kind: "item", entry, index: i + k }));
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
  entries: FeedEntry[];
}

function groupByDay(entries: FeedEntry[]): DayGroup[] {
  const groups: DayGroup[] = [];
  for (const entry of entries) {
    const { item } = entry;
    const key = item.publishedTs ? format(item.date, "yyyy-MM-dd") : "undated";
    const last = groups[groups.length - 1];
    if (last && last.key === key) {
      last.entries.push(entry);
    } else {
      groups.push({ key, label: key === "undated" ? "Undated" : dayLabel(item.date), entries: [entry] });
    }
  }
  return groups;
}

// One card per story. The pipeline links different outlets' tellings of the
// same story; the feed shows the primary telling (or, if that one isn't
// loaded, the earliest loaded member) and lists the rest as "also reported by".
export interface FeedEntry {
  item: NewsItem;
  others: StoryTelling[];
}

function collapseStories(items: NewsItem[]): FeedEntry[] {
  const byStory = new Map<string, NewsItem[]>();
  for (const item of items) {
    if (!item.storyId) continue;
    const list = byStory.get(item.storyId) ?? [];
    list.push(item);
    byStory.set(item.storyId, list);
  }
  const shown = new Set<string>();
  const entries: FeedEntry[] = [];
  for (const item of items) {
    if (!item.storyId) {
      entries.push({ item, others: [] });
      continue;
    }
    if (shown.has(item.storyId)) continue;
    shown.add(item.storyId);
    const members = byStory.get(item.storyId) ?? [item];
    const lead =
      members.find((m) => m.storyPrimary) ??
      [...members].sort((a, b) => a.date.getTime() - b.date.getTime())[0];
    const others: StoryTelling[] = lead.storyOthers
      ? lead.storyOthers
      : members
          .filter((m) => m !== lead)
          .map((m) => ({ source: m.source, sourceName: m.sourceName, title: m.title, url: m.url, date: m.date }));
    entries.push({ item: lead, others });
  }
  return entries;
}

interface TopicChipsProps {
  topics: Array<{ id: string; count: number }>;
  selectedTopic: string;
  onSelect: (topic: string) => void;
  /** Set on the selected chip so the compact bar can scroll it into view. */
  activeRef?: React.MutableRefObject<HTMLButtonElement | null>;
}

function TopicChips({ topics, selectedTopic, onSelect, activeRef }: TopicChipsProps) {
  const chip = (active: boolean) =>
    `shrink-0 text-[13px] px-2.5 py-1 rounded-full border transition-colors whitespace-nowrap ${
      active
        ? "border-primary/50 bg-primary/10 text-primary"
        : "border-border text-muted-foreground hover:text-foreground hover:bg-muted"
    }`;
  return (
    <>
      <button
        type="button"
        ref={!selectedTopic ? activeRef : undefined}
        onClick={() => onSelect("")}
        className={chip(!selectedTopic)}
      >
        All topics
      </button>
      {topics.map((topic) => (
        <button
          key={topic.id}
          type="button"
          ref={selectedTopic === topic.id ? activeRef : undefined}
          onClick={() => onSelect(topic.id)}
          className={chip(selectedTopic === topic.id)}
        >
          {topic.id}
          <span className="ml-1 text-[11px] opacity-70 tabular-nums">{topic.count}</span>
        </button>
      ))}
    </>
  );
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
  // Filter bar: sticks under the header so the reader never has to scroll back
  // to the top to change view or topic. Once stuck it collapses to a single
  // scrollable line to stay out of the way of the stories.
  const [filtersStuck, setFiltersStuck] = useState(false);
  // The compact bar shows one scrollable line; "All" opens every topic at once.
  const [barExpanded, setBarExpanded] = useState(false);
  const filtersTopRef = useRef<HTMLDivElement | null>(null);
  const filterBarRef = useRef<HTMLDivElement | null>(null);
  const activeChipRef = useRef<HTMLButtonElement | null>(null);
  const listTopRef = useRef<HTMLDivElement | null>(null);

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

  const selectView = (view: string) => {
    updateParams({ view: view === HEADLINES ? null : view, topic: null });
    if (filtersStuck) scrollToListTop();
  };
  const selectTopic = (topic: string) => {
    updateParams({ topic: topic === selectedTopic ? null : topic });
    if (filtersStuck) scrollToListTop();
  };

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

  // "Stuck" = the filter bar has reached its sticky offset under the header.
  useEffect(() => {
    let frame = 0;
    const measure = () => {
      frame = 0;
      const anchor = filtersTopRef.current;
      if (!anchor) return;
      setFiltersStuck(anchor.getBoundingClientRect().top <= headerHeight() + 1);
    };
    const onScroll = () => {
      if (!frame) frame = window.requestAnimationFrame(measure);
    };
    measure();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  // The compact bar scrolls sideways; keep the active chip in sight when it
  // appears, so the reader can see what is currently selected.
  useEffect(() => {
    if (!filtersStuck) {
      setBarExpanded(false);
      return;
    }
    if (barExpanded) return;
    const chip = activeChipRef.current;
    const strip = chip?.parentElement;
    if (!chip || !strip) return;
    if (!selectedTopic) {
      // Nothing is filtered: start the strip at the beginning so the reader
      // sees the views first, rather than centring the default chip.
      strip.scrollLeft = 0;
      return;
    }
    // Chase the selection only when it is actually off-screen.
    const chipBox = chip.getBoundingClientRect();
    const stripBox = strip.getBoundingClientRect();
    if (chipBox.left < stripBox.left || chipBox.right > stripBox.right) {
      chip.scrollIntoView({ block: "nearest", inline: "center" });
    }
  }, [filtersStuck, barExpanded, selectedTopic, selectedView]);

  // Changing a filter from the stuck bar replaces the whole list, so put the
  // reader at the start of the new list rather than leaving them mid-scroll.
  const scrollToListTop = useCallback(() => {
    // Measure after the re-render: picking a filter also collapses the
    // expanded bar, and its old height would put the list under the bar.
    window.requestAnimationFrame(() => {
      const list = listTopRef.current;
      if (!list) return;
      const offset = headerHeight() + (filterBarRef.current?.offsetHeight ?? 0) + 8;
      const top = list.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
    });
  }, []);

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
  // Stories collapse to one card; under a search the ranked order is kept.
  const entries = useMemo(() => collapseStories(results), [results]);
  const dayGroups = useMemo(
    () => (searchQuery ? [] : groupByDay([...entries].sort((a, b) => b.item.date.getTime() - a.item.date.getTime()))),
    [entries, searchQuery],
  );

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
          key={row.entry.item.id}
          item={row.entry.item}
          others={row.entry.others}
          index={row.index}
          selectedSmartGroup={selectedTopic}
          highlight={trimmedQuery}
          onSmartGroupClick={(group) => {
            selectTopic(group);
            scrollToListTop();
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
          {row.entries.length} more from {row.source}
        </button>
      ),
    );

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        {/* Page heading lives here rather than in the sticky header, so it
            scrolls away once the reader is in the stories. */}
        <div className="mb-3">
          <h1 className="text-[19px] md:text-[22px] font-semibold text-foreground">
            {vertical.heading}
          </h1>
          <p className="text-[13px] md:text-[15px] text-muted-foreground mt-0.5">
            {vertical.tagline}
          </p>
        </div>

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
            <TopicChips topics={topics} selectedTopic={selectedTopic} onSelect={selectTopic} />
          </div>
        )}

        {/* Once the filters above scroll out from under the header, the same
            controls return as a compact bar, so changing view or topic never
            means scrolling back to the top. It floats, so nothing shifts. */}
        <div ref={filtersTopRef} aria-hidden="true" />
        {filtersStuck && (
          <div
            ref={filterBarRef}
            style={{ top: "var(--app-header-h, 64px)" }}
            className="fixed left-0 right-0 z-40 border-b border-border bg-background/95 backdrop-blur-sm animate-fade-in"
          >
            <div className="container py-1 space-y-1">
              {/* Views on their own line… */}
              <div className="flex items-center gap-1.5 overflow-x-auto flex-nowrap scrollbar-none">
                {views.map((view) => (
                  <Button
                    key={view.id}
                    variant={selectedView === view.id ? "pillActive" : "pill"}
                    size="pill"
                    onClick={() => {
                      setBarExpanded(false);
                      selectView(view.id);
                    }}
                    className="font-sans shrink-0 h-7"
                  >
                    {view.label}
                  </Button>
                ))}
              </div>

              {/* …so topics get a line of their own and are visible on a phone
                  rather than pushed off the end of a shared row. */}
              {topics.length > 0 && (
                <div className="flex items-start gap-2">
                  <div
                    className={`flex items-center gap-1.5 min-w-0 flex-1 ${
                      barExpanded
                        ? "flex-wrap max-h-[45vh] overflow-y-auto"
                        : "flex-nowrap overflow-x-auto scrollbar-none"
                    }`}
                  >
                    <TopicChips
                      topics={topics}
                      selectedTopic={selectedTopic}
                      onSelect={(topic) => {
                        setBarExpanded(false);
                        selectTopic(topic);
                      }}
                      activeRef={activeChipRef}
                    />
                  </div>

                  <button
                    type="button"
                    onClick={() => setBarExpanded((open) => !open)}
                    aria-expanded={barExpanded}
                    aria-label={barExpanded ? "Show fewer topics" : "Show all topics"}
                    className="shrink-0 h-7 px-2 rounded-full border border-border text-[13px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors flex items-center gap-1"
                  >
                    {barExpanded ? "Less" : "All"}
                    <ChevronDown
                      className={`h-3.5 w-3.5 transition-transform ${barExpanded ? "rotate-180" : ""}`}
                    />
                  </button>
                </div>
              )}
            </div>
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
              <span className="text-muted-foreground"> · {entries.length} stories</span>
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

        <div ref={listTopRef} className="space-y-3">
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
              {renderRows(entries.map((entry, index) => ({ kind: "item", entry, index })))}
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
                  <span className="ml-2 font-normal normal-case tracking-normal">{group.entries.length}</span>
                </h2>
                {renderRows(
                  selectedView === RESEARCH
                    ? group.entries.map((entry, index) => ({ kind: "item" as const, entry, index }))
                    : toRows(group.entries, expandedBursts, group.key),
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
