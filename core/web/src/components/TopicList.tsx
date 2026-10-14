import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { NewsCard } from "@/components/NewsCard";
import { Topic } from "@/data/topicsData";

/** Topics shown before "Show more"; a big day has hundreds of single stories. */
export const TOPICS_PAGE_SIZE = 30;

function TopicRow({ topic }: { topic: Topic }) {
  const [open, setOpen] = useState(false);
  const panelId = `topic-${topic.id}`;
  const sources = topic.sourceCount === 1 ? "1 source" : `${topic.sourceCount} sources`;
  const stories = topic.size === 1 ? "1 story" : `${topic.size} stories`;
  return (
    <Card className="bg-card border-border" data-testid="topic">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={panelId}
        className="w-full text-left p-4 md:p-5 flex items-start gap-3 hover:bg-muted/40 transition-colors rounded-lg"
      >
        {open ? (
          <ChevronDown className="h-5 w-5 mt-0.5 shrink-0 text-primary" aria-hidden="true" />
        ) : (
          <ChevronRight className="h-5 w-5 mt-0.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        )}
        <span className="min-w-0">
          <span className="block text-[17px] md:text-lg font-semibold leading-snug text-foreground">
            {topic.title}
          </span>
          {topic.summary && (
            <span className="block mt-1 text-[15px] text-muted-foreground leading-relaxed">
              {topic.summary}
            </span>
          )}
          <span className="block mt-1.5 text-[13px] text-muted-foreground">
            {stories} · {sources}
          </span>
        </span>
      </button>
      {open && (
        <div id={panelId} className="px-4 pb-4 md:px-5 md:pb-5 space-y-3">
          {topic.stories.map((item, index) => (
            <NewsCard key={item.id} item={item} index={index} />
          ))}
        </div>
      )}
    </Card>
  );
}

export function TopicList({ topics }: { topics: Topic[] }) {
  const [shown, setShown] = useState(TOPICS_PAGE_SIZE);
  if (topics.length === 0) {
    return (
      <Card className="p-6 bg-card border-border text-center">
        <p className="text-[15px] text-muted-foreground">No topics for this day.</p>
      </Card>
    );
  }
  const remaining = topics.length - shown;
  return (
    <div className="space-y-3">
      {topics.slice(0, shown).map((topic) => (
        <TopicRow key={topic.id} topic={topic} />
      ))}
      {remaining > 0 && (
        <button
          type="button"
          onClick={() => setShown((value) => value + TOPICS_PAGE_SIZE)}
          className="w-full py-3 text-[15px] font-medium text-primary hover:underline"
        >
          Show more topics ({remaining} left)
        </button>
      )}
    </div>
  );
}
