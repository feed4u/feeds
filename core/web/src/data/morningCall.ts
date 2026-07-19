export interface MorningCallHighlight {
  title: string;
  link: string;
  source: string;
  published: string;
  smart_groups: string[];
  curated: boolean;
  publishedDate: Date;
}

export interface MorningCallData {
  generated_at: string;
  analysis_date: string;
  model: string;
  window_hours: number;
  source_file: string;
  source_generated_at?: string;
  source_days_back?: number;
  source_total_items?: number;
  total_items_in_window_all: number;
  total_items_in_window_curated: number;
  daily_report_markdown: string;
  highlights: MorningCallHighlight[];
}

function parseHighlightDate(input: string): Date {
  const parsed = new Date(input);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed;
  }
  return new Date();
}

async function fetchReportJson(): Promise<any> {
  const endpoints = [
    dataUrl("archive/daily_report_latest.json"),
    dataUrl("archive/morning_call_latest.json"),
  ];

  for (const url of endpoints) {
    const response = await fetch(url, {
      headers: { "Cache-Control": "no-cache" },
    });
    if (response.ok) {
      return response.json();
    }
  }
  throw new Error("Failed to load daily report from any known endpoint.");
}

export async function fetchMorningCall(): Promise<MorningCallData> {
  const data = await fetchReportJson();
  const markdown =
    data.daily_report_markdown ??
    data.morning_call_markdown ??
    "### Daily report unavailable\n\nNo content available.";

  // Filter out highlights with future dates
  const now = new Date();
  const highlights = (data.highlights || [])
    .map((item: MorningCallHighlight) => ({
      ...item,
      smart_groups: item.smart_groups || [],
      curated: Boolean(item.curated),
      publishedDate: parseHighlightDate(item.published),
    }))
    .filter((item: MorningCallHighlight) => item.publishedDate <= now);

  return {
    ...data,
    daily_report_markdown: markdown,
    highlights,
  };
}
import { dataUrl } from "./dataPaths";
