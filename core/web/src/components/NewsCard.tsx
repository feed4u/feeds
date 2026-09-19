import { Card } from "@/components/ui/card";
import { ExternalLink } from "lucide-react";
import { NewsItem, StoryTelling } from "@/data/newsData";
import { formatDistanceToNow } from "date-fns";
import { Fragment, ReactNode, useState } from "react";

const OTHERS_SHOWN = 4;

interface NewsCardProps {
  item: NewsItem;
  /** Other outlets' tellings of the same story. */
  others?: StoryTelling[];
  index: number;
  onSmartGroupClick?: (group: string) => void;
  selectedSmartGroup?: string;
  /** Current search query; matching text is highlighted so the reader can
   *  see why a story is in the results. */
  highlight?: string;
}

function highlightText(text: string, query?: string): ReactNode {
  const q = query?.trim();
  if (!q) return text;
  const lower = text.toLowerCase();
  const needle = q.toLowerCase();
  const parts: ReactNode[] = [];
  let pos = 0;
  let idx = lower.indexOf(needle, pos);
  if (idx === -1) return text;
  while (idx !== -1) {
    parts.push(<Fragment key={`t${pos}`}>{text.slice(pos, idx)}</Fragment>);
    parts.push(
      <mark key={`m${idx}`} className="bg-primary/25 text-inherit rounded-sm px-0.5">
        {text.slice(idx, idx + needle.length)}
      </mark>,
    );
    pos = idx + needle.length;
    idx = lower.indexOf(needle, pos);
  }
  parts.push(<Fragment key={`t${pos}`}>{text.slice(pos)}</Fragment>);
  return parts;
}

export function NewsCard({ item, others = [], index, onSmartGroupClick, selectedSmartGroup, highlight }: NewsCardProps) {
  const [showAllOthers, setShowAllOthers] = useState(false);
  const visibleOthers = showAllOthers ? others : others.slice(0, OTHERS_SHOWN);
  const hiddenCount = others.length - visibleOthers.length;
  return (
    <Card
      className="group p-4 md:p-5 gradient-card border-border hover:border-primary/30 transition-all duration-300 animate-fade-in"
      style={{ animationDelay: `${Math.min(index, 20) * 40}ms` }}
    >
      <h3 className="text-[17px] md:text-lg font-semibold leading-snug text-foreground group-hover:text-primary transition-colors">
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-start gap-2"
        >
          <span>{highlightText(item.title, highlight)}</span>
          <ExternalLink className="h-4 w-4 shrink-0 opacity-30 group-hover:opacity-100 transition-opacity mt-1" />
        </a>
      </h3>

      <p className="mt-1.5 text-[13px] text-muted-foreground">
        <span className="font-medium text-foreground/80">{highlightText(item.sourceName, highlight)}</span>
        <span aria-hidden="true"> · </span>
        <time dateTime={item.published ?? undefined}>
          {formatDistanceToNow(item.date, { addSuffix: true })}
        </time>
      </p>

      {item.summary && (
        <p className="mt-2 text-[15px] text-muted-foreground leading-relaxed line-clamp-3">
          {highlightText(item.summary, highlight)}
        </p>
      )}

      {others.length > 0 && (
        <p className="mt-2 text-[13px] text-muted-foreground">
          <span className="font-medium text-foreground/70">Also reported by</span>{" "}
          {visibleOthers.map((o, i) => (
            <Fragment key={o.url}>
              {i > 0 && ", "}
              <a
                href={o.url}
                target="_blank"
                rel="noopener noreferrer"
                title={o.title}
                className="hover:text-primary hover:underline"
              >
                {o.sourceName}
              </a>
            </Fragment>
          ))}
          {hiddenCount > 0 && (
            <>
              {" "}
              <button
                type="button"
                onClick={() => setShowAllOthers(true)}
                className="text-primary hover:underline"
              >
                +{hiddenCount} more
              </button>
            </>
          )}
        </p>
      )}

      {item.smartGroups.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {item.smartGroups.map((group) => {
            const isSelected = selectedSmartGroup === group;
            return (
              <button
                key={group}
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  onSmartGroupClick?.(group);
                }}
                className={`text-[12px] px-2 py-0.5 rounded-full transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-primary text-primary-foreground font-semibold'
                    : 'text-muted-foreground bg-muted/60 hover:bg-muted hover:text-foreground'
                }`}
              >
                {group}
              </button>
            );
          })}
        </div>
      )}
    </Card>
  );
}
