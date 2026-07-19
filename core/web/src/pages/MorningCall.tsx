import { useState, useEffect, Fragment, ReactNode } from "react";
import { vertical } from "@/config/verticals";
import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Helmet } from "react-helmet-async";
import { format, formatDistanceToNow } from "date-fns";
import { Calendar, Shield, AlertTriangle, TrendingUp, Terminal } from "lucide-react";
import { fetchMorningCall, MorningCallData, MorningCallHighlight } from "@/data/morningCall";

function renderInlineTokens(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={`bold-${index}`}>{part.slice(2, -2)}</strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={`code-${index}`} className="px-1 py-0.5 bg-muted rounded">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <Fragment key={`text-${index}`}>{part}</Fragment>;
  });
}

function SimpleMarkdown({ content }: { content: string }) {
  const lines = content.split("\n");
  const elements: ReactNode[] = [];
  let currentList: string[] = [];

  const flushList = () => {
    if (currentList.length === 0) return;
    elements.push(
      <ul key={`list-${elements.length}`} className="list-disc pl-6 space-y-1">
        {currentList.map((item, idx) => (
          <li key={`li-${idx}`} className="text-[15px] text-muted-foreground">
            {renderInlineTokens(item)}
          </li>
        ))}
      </ul>,
    );
    currentList = [];
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    if (trimmed.startsWith("###")) {
      flushList();
      elements.push(
        <h3 key={`h-${index}`} className="text-xl font-semibold text-foreground mt-6">
          {trimmed.replace(/^###\s*/, "")}
        </h3>,
      );
      return;
    }

    if (trimmed.startsWith("- ")) {
      currentList.push(trimmed.replace(/^-+\s*/, ""));
      return;
    }

    if (trimmed === "") {
      flushList();
      return;
    }

    flushList();
    elements.push(
      <p key={`p-${index}`} className="text-[15px] text-muted-foreground">
        {renderInlineTokens(trimmed)}
      </p>,
    );
  });

  flushList();

  return <div className="space-y-3">{elements}</div>;
}

function HighlightCard({ highlight }: { highlight: MorningCallHighlight }) {
  return (
    <Card className="p-5 bg-card border-border">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[13px] font-mono text-muted-foreground uppercase">
            {highlight.source}
          </p>
          <a
            href={highlight.link}
            target="_blank"
            rel="noopener noreferrer"
            className="text-lg font-semibold text-foreground hover:text-primary transition-colors"
          >
            {highlight.title}
          </a>
        </div>
        <span className="text-[13px] text-muted-foreground font-mono">
          {formatDistanceToNow(highlight.publishedDate, { addSuffix: true })}
        </span>
      </div>

      {highlight.smart_groups.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {highlight.smart_groups.map((group) => (
            <Badge key={group} variant="category" className="text-[12px]">
              #{group}
            </Badge>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function MorningCall() {
  const [data, setData] = useState<MorningCallData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const payload = await fetchMorningCall();
        setData(payload);
        setError(null);
      } catch (err) {
        console.error("Failed to load daily report data:", err);
        setError("Daily report is unavailable right now.");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const stats = {
    curated: data?.total_items_in_window_curated ?? 0,
    total: data?.total_items_in_window_all ?? 0,
    highlights: data?.highlights.length ?? 0,
  };

  return (
    <Layout>
      <Helmet>
        <title>Daily Report — {vertical.metaTitle}</title>
        <meta
          name="description"
          content="Daily SOC-ready security report generated from curated intelligence."
        />
      </Helmet>

      <div className="space-y-6">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <Calendar className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-3xl font-bold text-foreground">Daily Report Briefing</h1>
              <p className="text-[15px] text-muted-foreground">
                {data
                  ? `Published ${format(new Date(data.generated_at), "MMMM d, yyyy 'at' HH:mm")} UTC`
                  : "Latest curated overview for SOC teams"}
              </p>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 bg-card rounded-lg border border-border">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent mb-4" />
            <p className="text-[15px] text-muted-foreground font-mono">
              Loading daily report...
            </p>
          </div>
        ) : error ? (
          <div className="text-center py-12 bg-card rounded-lg border border-destructive">
            <p className="text-[15px] text-destructive font-mono">{error}</p>
          </div>
        ) : data ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-5 bg-card border-border flex items-center gap-3">
                <Shield className="h-8 w-8 text-primary" />
                <div>
                  <p className="text-[13px] text-muted-foreground font-mono uppercase">
                    Curated Items
                  </p>
                  <p className="text-2xl font-bold text-foreground">{stats.curated}</p>
                </div>
              </Card>
              <Card className="p-5 bg-card border-border flex items-center gap-3">
                <AlertTriangle className="h-8 w-8 text-destructive" />
                <div>
                  <p className="text-[13px] text-muted-foreground font-mono uppercase">
                    Window Coverage
                  </p>
                  <p className="text-2xl font-bold text-foreground">
                    {stats.total} items
                  </p>
                </div>
              </Card>
              <Card className="p-5 bg-card border-border flex items-center gap-3">
                <TrendingUp className="h-8 w-8 text-success" />
                <div>
                  <p className="text-[13px] text-muted-foreground font-mono uppercase">
                    Highlighted Stories
                  </p>
                  <p className="text-2xl font-bold text-foreground">{stats.highlights}</p>
                </div>
              </Card>
            </div>

            <Card className="p-6 bg-card border-border">
              <div className="flex items-center gap-2 mb-4">
                <Terminal className="h-5 w-5 text-primary" />
                <h2 className="text-xl font-semibold text-foreground">
                  SOC Daily Report ({data.window_hours}h window)
                </h2>
              </div>
              <SimpleMarkdown content={data.daily_report_markdown} />
            </Card>

            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                <h2 className="text-xl font-semibold text-foreground">Top Highlights</h2>
              </div>
              {data.highlights.length === 0 ? (
                <Card className="p-6 bg-card border-border text-center">
                  <p className="text-[15px] text-muted-foreground">
                    No curated highlights were generated for this window.
                  </p>
                </Card>
              ) : (
                <div className="space-y-4">
                  {data.highlights.map((highlight) => (
                    <HighlightCard key={`${highlight.link}-${highlight.published}`} highlight={highlight} />
                  ))}
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </Layout>
  );
}
