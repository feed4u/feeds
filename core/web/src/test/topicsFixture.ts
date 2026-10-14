import { TopicsPayload } from "@/data/topicsData";

const story = (n: number, title: string, source: string) => ({
  title,
  summary: `Summary of ${title}.`,
  link: `https://news.example/${n}`,
  source,
  type: "news",
  type_label: "News",
  feed_type: "news",
  published: "2026-10-12T12:00:00+00:00",
  published_ts: 1791806400 + n * 60,
  smart_groups: [],
  curated: false,
});

/** The shape build_topics.py writes (schema_version 1). */
export function topicsFixture(extraSingles = 0): TopicsPayload {
  const singles = Array.from({ length: extraSingles }, (_, i) => {
    const n = 100 + i;
    return {
      id: `single${n}`,
      rank: 3 + i,
      title: `Single story ${n}`,
      summary: `Summary of single story ${n}.`,
      origin: "rules" as const,
      size: 1,
      source_count: 1,
      sources: ["Outlet"],
      first_ts: null,
      latest_ts: null,
      score: 3,
      stories: [story(n, `Single story ${n}`, "Outlet")],
    };
  });
  const topics = [
    {
      id: "exch0001",
      rank: 1,
      title: "Microsoft patches exploited Exchange zero-day",
      summary: "Microsoft fixed an Exchange Server flaw that attackers already used.",
      origin: "llm" as const,
      size: 3,
      source_count: 3,
      sources: ["BleepingComputer", "SecurityWeek", "The Record"],
      first_ts: 1791806400,
      latest_ts: 1791806580,
      score: 9,
      stories: [
        story(1, "Microsoft patches Exchange Server zero-day exploited in attacks", "BleepingComputer"),
        story(2, "Emergency fix for Exchange flaw already used by hackers", "SecurityWeek"),
        story(3, "Exchange zero-day exploited in attacks, Microsoft patches", "The Record"),
      ],
    },
    {
      id: "chrome01",
      rank: 2,
      title: "Google releases Chrome 130 with new tab grouping features",
      summary: "Google released Chrome 130.",
      origin: "rules" as const,
      size: 1,
      source_count: 1,
      sources: ["The Verge"],
      first_ts: 1791806640,
      latest_ts: 1791806640,
      score: 3,
      stories: [story(4, "Google releases Chrome 130 with new tab grouping features", "The Verge")],
    },
    ...singles,
  ];
  return {
    schema_version: 1,
    vertical: "k5",
    date: "2026-10-12",
    generated_at: "2026-10-13T01:40:00+00:00",
    mode: "llm",
    model: "qwen38-27b-mtp2:latest",
    stats: {
      items: topics.reduce((sum, t) => sum + t.size, 0),
      topics: topics.length,
      multi_story_topics: 1,
      singletons: topics.length - 1,
      largest_topic: 3,
    },
    topics,
  };
}
