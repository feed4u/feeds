import { useEffect, useMemo, useState } from "react";
import { Helmet } from "react-helmet-async";
import { Layout } from "@/components/Layout";
import { fetchNewsChunk, NewsItem } from "@/data/newsData";
import { vertical } from "@/config/verticals";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const DAYS_BACK = 7;

type Grouped = {
  key: string;
  title: string;
  items: NewsItem[];
  domains: string[];
  baseDomains: string[];
  mediaGroups: string[]; // consortium/id
};

function normalizeTitle(title: string): string {
  let t = title.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  t = t.replace(/[“”\"']/g, "").replace(/[\s]+/g, " ").trim();
  // strip trailing site delimiter patterns
  const cutIdx = [" - ", " – ", " | "]
    .map((sep) => t.lastIndexOf(sep))
    .filter((i) => i > 0)
    .reduce((a, b) => Math.max(a, b), -1);
  if (cutIdx > 20) t = t.slice(0, cutIdx).trim();
  return t;
}

function baseDomain(url: string): string {
  try {
    const u = new URL(url);
    const parts = u.hostname.split('.');
    if (parts.length >= 2) return parts.slice(-2).join('.');
    return u.hostname;
  } catch {
    return "";
  }
}

// Very lightweight consortium mapping for Finland
function mediaGroupFromDomain(host: string): string {
  const d = host.replace(/^www\./, "");
  if (/\b(is|hs|taloussanomat|iltasanomat)\.fi$/.test(d)) return "Sanoma";
  if (/\b(iltalehti|kauppalehti|talouselama)\.fi$/.test(d)) return "Alma Media";
  if (/\byle\.fi$/.test(d)) return "Yle";
  if (/\bmtv\.fi$/.test(d)) return "MTV";
  return d; // fallback: domain acts as its own group id
}

// Load recent items by following the chunk chain from latest.json into the
// daily archives, stopping once the window is covered.
async function fetchRecentItems(daysBack: number): Promise<NewsItem[]> {
  const cutoff = Date.now() / 1000 - daysBack * 86400;
  const seen = new Set<string>();
  const items: NewsItem[] = [];
  let path: string | null | undefined = undefined; // undefined → latest.json

  for (let i = 0; i <= daysBack; i++) {
    const chunk = await fetchNewsChunk(path ?? undefined);
    for (const it of chunk.items) {
      if ((it.publishedTs ?? 0) < cutoff) continue;
      if (seen.has(it.url)) continue;
      seen.add(it.url);
      items.push(it);
    }
    if (!chunk.nextChunk) break;
    // stop once the chunk chain has moved past the window
    const oldest = Math.min(...chunk.items.map((it) => it.publishedTs ?? Infinity));
    if (Number.isFinite(oldest) && oldest < cutoff) break;
    path = chunk.nextChunk;
  }
  return items;
}

export default function Duplicates() {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [minCount, setMinCount] = useState(2);
  const [view, setView] = useState<"all" | "syndicated" | "cross">("all");

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const recent = await fetchRecentItems(DAYS_BACK);
        setItems(recent.filter((it) => (it.feedType || 'news').toLowerCase() === 'news'));
        setError(null);
      } catch (e: any) {
        setError(e?.message || 'Failed to load data');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const groups = useMemo<Grouped[]>(() => {
    const byKey: Record<string, Grouped> = {};
    items.forEach((it) => {
      const key = normalizeTitle(it.title);
      const dom = (() => {
        try { return new URL(it.url).hostname.replace(/^www\./, ""); } catch { return ""; }
      })();
      const base = baseDomain(it.url);
      const g = mediaGroupFromDomain(dom || base);
      if (!byKey[key]) {
        byKey[key] = { key, title: it.title, items: [], domains: [], baseDomains: [], mediaGroups: [] };
      }
      byKey[key].items.push(it);
      if (dom && !byKey[key].domains.includes(dom)) byKey[key].domains.push(dom);
      if (base && !byKey[key].baseDomains.includes(base)) byKey[key].baseDomains.push(base);
      if (g && !byKey[key].mediaGroups.includes(g)) byKey[key].mediaGroups.push(g);
    });
    // convert to array
    return Object.values(byKey)
      .filter((g) => g.items.length >= minCount)
      .sort((a, b) => b.items.length - a.items.length);
  }, [items, minCount]);

  const filtered = useMemo(() => {
    if (view === 'all') return groups;
    if (view === 'syndicated') {
      // Mostly same consortium: single mediaGroup or all base domains equal
      return groups.filter((g) => g.mediaGroups.length === 1 || g.baseDomains.length === 1);
    }
    // cross-media coverage: many independent groups/domains
    return groups.filter((g) => g.mediaGroups.length >= 2 && g.baseDomains.length >= 2);
  }, [groups, view]);

  return (
    <Layout>
      <Helmet>
        <title>Duplicates — {vertical.metaTitle}</title>
        <meta name="description" content="Grouped duplicates across media: syndicated vs cross‑media coverage." />
      </Helmet>

      <div className="flex items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-2">
          <Button variant={view === 'all' ? 'default' : 'outline'} size="sm" onClick={() => setView('all')}>All</Button>
          <Button variant={view === 'syndicated' ? 'default' : 'outline'} size="sm" onClick={() => setView('syndicated')}>Syndicated</Button>
          <Button variant={view === 'cross' ? 'default' : 'outline'} size="sm" onClick={() => setView('cross')}>Cross‑media</Button>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Min. articles</span>
          <select
            value={minCount}
            onChange={(e) => setMinCount(parseInt(e.target.value, 10))}
            className="h-9 rounded-md border border-border bg-background px-2"
          >
            {[2,3,4,5,6,7,8,9,10].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
      </div>

      {loading && (
        <div className="text-center py-12 bg-card rounded-lg border border-border">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent mb-4"></div>
          <p className="text-[15px] text-muted-foreground font-mono">Loading…</p>
        </div>
      )}
      {error && !loading && (
        <div className="text-center py-12 bg-card rounded-lg border border-destructive">
          <p className="text-[15px] text-destructive font-mono">{error}</p>
        </div>
      )}

      {!loading && !error && (
        <div className="space-y-4">
          {filtered.map((g) => (
            <Card key={g.key} className="p-4 border-border">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold text-foreground mb-1">{g.title}</h3>
                  <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <Badge variant="outline" className="text-xs">{g.items.length} articles</Badge>
                    <Badge variant="outline" className="text-xs">{g.baseDomains.length} domains</Badge>
                    <Badge variant="outline" className="text-xs">{g.mediaGroups.length} media groups</Badge>
                    {g.mediaGroups.length === 1 || g.baseDomains.length === 1 ? (
                      <Badge variant="secondary" className="text-xs">Syndicated</Badge>
                    ) : (
                      <Badge variant="secondary" className="text-xs">Cross‑media</Badge>
                    )}
                  </div>
                </div>
              </div>
              <Separator className="my-3" />
              <div className="grid gap-2 md:grid-cols-2">
                {g.items
                  .slice() // copy
                  .sort((a,b) => (b.publishedTs ?? 0) - (a.publishedTs ?? 0))
                  .map((it, idx) => {
                    const host = (() => { try { return new URL(it.url).hostname.replace(/^www\./, ""); } catch { return it.source; }})();
                    return (
                      <div key={idx} className="flex items-center justify-between gap-4 text-[13px]">
                        <a href={it.url} target="_blank" rel="noopener noreferrer" className="text-foreground hover:text-primary truncate" title={it.title}>
                          {host}
                        </a>
                        <span className="text-muted-foreground tabular-nums">
                          {it.published?.slice(0, 16) ?? ''}
                        </span>
                      </div>
                    );
                  })}
              </div>
            </Card>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-12 bg-card rounded-lg border border-border">
              <p className="text-[15px] text-muted-foreground font-mono">No groups match the current filters.</p>
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}
