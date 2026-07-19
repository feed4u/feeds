import { dataUrl } from "./dataPaths";
import { NewsItem, RawNewsItem, toNewsItem } from "./newsData";

const MAX_YEARS_BACK = 8;
const MAX_YEARS_AHEAD = 1;

async function fetchYearlyFile(year: number, feedType: string): Promise<NewsItem[]> {
  const response = await fetch(dataUrl(`archive/${feedType}/yearly/${year}.json`), {
    headers: {
      "Cache-Control": "no-cache",
    },
  });

  if (!response.ok) {
    return [];
  }

  const data: RawNewsItem[] = await response.json();
  if (!Array.isArray(data)) {
    return [];
  }

  return data.map((item, index) => toNewsItem(item, index));
}

export async function fetchArchiveData(feedType: string = "news"): Promise<NewsItem[]> {
  const now = new Date();
  const currentYear = now.getFullYear();
  const yearsToTry: number[] = [];

  for (let offset = MAX_YEARS_AHEAD; offset >= -MAX_YEARS_BACK; offset--) {
    yearsToTry.push(currentYear + offset);
  }

  const results = await Promise.all(
    yearsToTry.map(async (year) => {
      try {
        return await fetchYearlyFile(year, feedType);
      } catch {
        return [];
      }
    }),
  );

  const merged = results.flat();
  const dedupByUrl = new Map<string, NewsItem>();

  merged.forEach((item) => {
    const key = item.url || `${item.title}-${item.publishedTs}`;
    const existing = dedupByUrl.get(key);
    if (!existing || existing.date < item.date) {
      dedupByUrl.set(key, item);
    }
  });

  // Filter out future dates (reuse 'now' from above)
  const filtered = Array.from(dedupByUrl.values()).filter(item => {
    // Keep items with epoch 0 (no valid date)
    if (item.publishedTs === 0) return true;

    // Filter out items with dates in the future
    return item.date <= now;
  });

  return filtered.sort((a, b) => b.date.getTime() - a.date.getTime());
}
