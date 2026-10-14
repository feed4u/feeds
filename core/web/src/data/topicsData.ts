import { dataUrl } from "./dataPaths";
import { NewsItem, RawNewsItem, toNewsItem } from "./newsData";

/** archive/news/topics/<date>.json, written by core/code/base/build_topics.py. */
export interface RawTopic {
  id: string;
  rank: number;
  title: string;
  summary: string;
  origin: "llm" | "rules";
  size: number;
  source_count: number;
  sources: string[];
  first_ts: number | null;
  latest_ts: number | null;
  score: number;
  stories: RawNewsItem[];
}

export interface TopicsPayload {
  schema_version: number;
  vertical: string;
  date: string;
  generated_at: string;
  mode: "llm" | "partial" | "rules";
  model: string | null;
  stats: {
    items: number;
    topics: number;
    multi_story_topics: number;
    singletons: number;
    largest_topic: number;
  };
  topics: RawTopic[];
}

export interface Topic {
  id: string;
  rank: number;
  title: string;
  summary: string;
  size: number;
  sourceCount: number;
  stories: NewsItem[];
}

export interface TopicsDay {
  date: string;
  generatedAt: Date;
  mode: TopicsPayload["mode"];
  totalStories: number;
  topics: Topic[];
}

export const TOPICS_SCHEMA_VERSION = 1;

export function toTopicsDay(payload: TopicsPayload): TopicsDay {
  if (payload.schema_version !== TOPICS_SCHEMA_VERSION || !Array.isArray(payload.topics)) {
    throw new Error(`Unsupported topics file (schema ${payload.schema_version})`);
  }
  return {
    date: payload.date,
    generatedAt: new Date(payload.generated_at),
    mode: payload.mode,
    totalStories: payload.stats?.items ?? 0,
    topics: payload.topics.map((topic) => ({
      id: topic.id,
      rank: topic.rank,
      title: topic.title,
      summary: topic.summary,
      size: topic.size,
      sourceCount: topic.source_count,
      stories: topic.stories.map((story, index) => toNewsItem(story, index)),
    })),
  };
}

export async function fetchTopics(): Promise<TopicsDay> {
  const response = await fetch(dataUrl("archive/news/topics/topics_latest.json"), {
    headers: { "Cache-Control": "no-cache" },
  });
  if (!response.ok) {
    throw new Error(`Failed to load topics: ${response.status}`);
  }
  return toTopicsDay(await response.json());
}
