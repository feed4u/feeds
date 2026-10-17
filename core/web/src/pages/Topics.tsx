import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { format, parseISO } from "date-fns";
import { Layers } from "lucide-react";
import { vertical } from "@/config/verticals";
import { Layout } from "@/components/Layout";
import { TopicList } from "@/components/TopicList";
import { fetchTopics } from "@/data/topicsData";

export default function Topics() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["topics", "latest"],
    queryFn: fetchTopics,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const day = data ? format(parseISO(data.date), "EEEE, MMMM d") : null;
  const heading = day ? `Topics for ${day}` : "Topics";
  const multi = data ? data.topics.filter((topic) => topic.size > 1).length : 0;

  return (
    <Layout>
      <Helmet>
        <title>{heading} — {vertical.metaTitle}</title>
        <meta
          name="description"
          content={`The day's stories from ${vertical.logoText.primary}${vertical.logoText.suffix}, grouped by topic.`}
        />
      </Helmet>

      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Layers className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold text-foreground">{heading}</h1>
            <p className="text-[15px] text-muted-foreground">
              {data
                ? `${data.totalStories} stories from ${day} (UTC) in ${data.topics.length} topics, ${multi} reported more than once. Open a topic to see its stories.`
                : "The day's stories, grouped by topic"}
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="text-center py-12 bg-card rounded-lg border border-border">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent mb-4" />
            <p className="text-[15px] text-muted-foreground font-mono">Loading topics...</p>
          </div>
        ) : isError || !data ? (
          <div className="text-center py-12 bg-card rounded-lg border border-border">
            <p className="text-[15px] text-muted-foreground">
              Topics are not available yet. They are built once a day.
            </p>
          </div>
        ) : (
          <TopicList topics={data.topics} />
        )}
      </div>
    </Layout>
  );
}
