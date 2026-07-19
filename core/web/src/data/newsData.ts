export interface NewsItem {
  id: string;
  title: string;
  source: string;
  category: string;
  feedType: string;
  smartGroups: string[];
  date: Date;
  summary: string;
  url: string;
  curated?: boolean;
  published?: string | null;
  publishedTs?: number | null;
}

export interface NewsDataResponse {
  generated_at: string;
  days_back: number;
  total_items: number;
  items: RawNewsItem[];
  feed_types?: string[];
  // present in latest.json and archive pages for pagination
  next_chunk?: string | null;
}

export interface RawNewsItem {
  title: string;
  summary?: string;
  summary_html?: string;
  link: string;
  source: string;
  type: string;
  type_label?: string;
  published?: string;
  published_ts?: number;
  smart_groups?: string[];
  curated?: boolean;
  feed_type?: string;
}

export interface CategoryMetadata {
  generated_at: string;
  source: string;
  total_categories: number;
  slug_to_label: Record<string, string>;
  feed_types?: string[];
  hierarchy?: Record<string, FeedCategory[]>;
  sources?: Record<string, string>;
  categories: Array<{
    id: string;
    label: string;
    slug: string;
  }>;
}

export interface FeedCategory {
  label: string;
  slug: string;
  feeds: Array<{
    title: string;
    xml_url: string;
    html_url: string;
  }>;
}

import { dataUrl } from "./dataPaths";
import { deriveSmartGroupsFromText } from "./smart-group-rules";

const FEED_TYPE_LABELS: Record<string, string> = {
  news: "News",
  blog: "Blogs",
  blogs: "Blogs",
  podcast: "Podcasts",
  podcasts: "Podcasts",
};

// Category metadata loaded from backend
let categoryMetadata: CategoryMetadata | null = null;

// Load category metadata from the backend
async function loadCategoryMetadata(): Promise<CategoryMetadata> {
  if (categoryMetadata) {
    return categoryMetadata;
  }

  try {
    const response = await fetch(dataUrl('category_metadata.json'));
    if (!response.ok) {
      console.warn('Failed to load category metadata, using defaults');
      return createDefaultMetadata();
    }
    categoryMetadata = await response.json();
    return categoryMetadata!;
  } catch (error) {
    console.warn('Error loading category metadata:', error);
    return createDefaultMetadata();
  }
}

// Create default metadata as fallback
function createDefaultMetadata(): CategoryMetadata {
  return {
    generated_at: new Date().toISOString(),
    source: 'fallback',
    total_categories: 0,
    slug_to_label: {},
    categories: [],
  };
}

// Get category label from slug
export function getCategoryLabel(slug: string): string {
  if (categoryMetadata?.slug_to_label[slug]) {
    return categoryMetadata.slug_to_label[slug];
  }
  // Fallback: capitalize slug
  return slug.split('-').map(word =>
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
}

export function formatFeedTypeLabel(type: string): string {
  const key = type.toLowerCase();
  return FEED_TYPE_LABELS[key] || key.charAt(0).toUpperCase() + key.slice(1);
}

const FALLBACK_SUMMARY = "No summary provided for this entry.";

function getPublishedDate(raw: RawNewsItem): { date: Date; publishedTs: number | null } {
  if (typeof raw.published_ts === "number") {
    const byTs = new Date(raw.published_ts * 1000);
    if (!Number.isNaN(byTs.getTime())) {
      return { date: byTs, publishedTs: raw.published_ts };
    }
  }

  if (raw.published) {
    const parsed = new Date(raw.published);
    if (!Number.isNaN(parsed.getTime())) {
      return { date: parsed, publishedTs: Math.floor(parsed.getTime() / 1000) };
    }
  }

  // For items without valid dates, use epoch 0 so they sort to the bottom
  // instead of appearing at the top with "current time"
  const fallback = new Date(0);
  return { date: fallback, publishedTs: 0 };
}

// Transform raw news item to the format expected by the UI
export function toNewsItem(raw: RawNewsItem, index: number): NewsItem {
  const { date, publishedTs } = getPublishedDate(raw);
  const safeIdBase = publishedTs ?? Date.now();
  const title = raw.title;
  const summaryText = (raw.summary_html || raw.summary || "").toString();
  const backendGroups: string[] = Array.isArray(raw.smart_groups) ? raw.smart_groups : [];
  const fallbackGroups = backendGroups.length ? backendGroups : deriveSmartGroupsFromText(title, summaryText, raw.source);
  return {
    id: `${safeIdBase}-${index}-${raw.link}`,
    title,
    source: raw.source,
    category: raw.type, // Use type directly as category slug
    feedType: raw.feed_type ?? "news",
    smartGroups: fallbackGroups,
    date,
    summary: raw.summary?.trim() || FALLBACK_SUMMARY,
    url: raw.link,
    curated: Boolean(raw.curated),
    published: raw.published ?? null,
    publishedTs,
  };
}

// Fetch news data from the JSON file (uses latest.json for chunked loading)
export async function fetchNewsData(): Promise<{
  items: NewsItem[];
  generatedAt: Date;
  daysBack: number;
  totalItems: number;
  feedTypes: string[];
}> {
  // Load category metadata first
  await loadCategoryMetadata();

  const response = await fetch(dataUrl('latest.json'));

  if (!response.ok) {
    throw new Error(`Failed to fetch news data: ${response.status}`);
  }

  const data: NewsDataResponse = await response.json();

  // Map items and filter out future dates
  const now = new Date();
  const mappedItems = data.items.map((item, index) => toNewsItem(item, index));
  const filteredItems = mappedItems.filter(item => {
    // Keep items with epoch 0 (no valid date)
    if (item.publishedTs === 0) return true;

    // Filter out items with dates in the future
    return item.date <= now;
  });

  const explicitFeedTypes = data.feed_types && data.feed_types.length > 0
    ? data.feed_types
    : Array.from(new Set(filteredItems.map((item) => item.feedType)));

  return {
    items: filteredItems,
    generatedAt: new Date(data.generated_at),
    daysBack: data.days_back,
    totalItems: data.total_items,
    feedTypes: explicitFeedTypes.length ? explicitFeedTypes : ["news"],
  };
}

// Paginated chunk fetcher for infinite scroll
export async function fetchNewsChunk(relativePath?: string): Promise<{
  items: NewsItem[];
  nextChunk: string | null;
  generatedAt: Date;
  totalItems: number;
  feedTypes: string[];
}> {
  await loadCategoryMetadata();

  const path = relativePath ?? 'latest.json';
  const res = await fetch(dataUrl(path));
  if (!res.ok) {
    throw new Error(`Failed to fetch ${path}: ${res.status}`);
  }
  const data: NewsDataResponse = await res.json();

  const now = new Date();
  const mapped = data.items.map((item, idx) => toNewsItem(item, idx));
  const filtered = mapped.filter((item) => item.publishedTs === 0 || item.date <= now);

  // Determine feed types for this page
  const feedTypes = data.feed_types && data.feed_types.length
    ? data.feed_types
    : Array.from(new Set(filtered.map((i) => i.feedType)));

  const nextChunk = typeof (data as any).next_chunk === 'string' ? (data as any).next_chunk : null;

  return {
    items: filtered,
    nextChunk,
    generatedAt: new Date(data.generated_at),
    totalItems: data.total_items,
    feedTypes: feedTypes.length ? feedTypes : ["news"],
  };
}

// Export category metadata for use by other components
export { loadCategoryMetadata, categoryMetadata };

// Export empty arrays for initial state
export const newsItems: NewsItem[] = [];
export const categories: Array<{ id: string; label: string; count: number }> = [];
export const smartGroups: Array<{ id: string; label: string; count: number }> = [];
