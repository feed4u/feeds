import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HelmetProvider } from "react-helmet-async";
import MorningCall from "@/pages/MorningCall";
import { SearchProvider } from "@/contexts/SearchContext";

// The real published 4u report the outcome check's frozen day comes from.
const REAL_REPORT = resolve(__dirname, "../../../data/4u/archive/daily_report_2026-10-20.json");
const LINKS_PER_SECTION = 4; // daily_briefing.LINKS_PER_BULLET

interface ReportJson {
  analysis_date: string;
  daily_report_markdown: string;
  top_stories: { title: string; links: string[] }[];
  highlights: { link: string; published: string }[];
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={client}>
        <MemoryRouter
          initialEntries={["/morning-call"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <SearchProvider>
            <MorningCall />
          </SearchProvider>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

function serve(report: unknown) {
  const fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify(report), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function hrefs(root: HTMLElement): Set<string> {
  return new Set(within(root).queryAllByRole("link").map((a) => a.getAttribute("href") ?? ""));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("Morning Call page", () => {
  it.skipIf(!existsSync(REAL_REPORT))("renders every section link and highlight of the real 4u report", async () => {
    const report: ReportJson = JSON.parse(readFileSync(REAL_REPORT, "utf-8"));
    const fetchMock = serve(report);
    const { container } = renderPage();

    expect(await screen.findByText(`Briefing for ${report.analysis_date} (UTC)`)).toBeInTheDocument();
    for (const story of report.top_stories) {
      expect(screen.getByRole("heading", { level: 3, name: story.title })).toBeInTheDocument();
    }
    const shown = hrefs(container);
    const sectionLinks = report.top_stories.flatMap((s) =>
      s.links.slice(0, LINKS_PER_SECTION).map((l) => l.replace(/\)/g, "%29").replace(/ /g, "%20")),
    );
    expect(sectionLinks.length).toBeGreaterThan(0);
    for (const link of sectionLinks) expect(shown).toContain(link);
    for (const highlight of report.highlights) expect(shown).toContain(highlight.link);
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/archive\/daily_report_latest\.json$/);
  });

  it("loads again on a fresh visit", async () => {
    const report = {
      generated_at: "2026-10-21T01:40:00Z", analysis_date: "2026-10-20", model: "m", window_hours: 24,
      source_file: "", total_items_in_window_all: 1, total_items_in_window_curated: 0,
      daily_report_markdown: "### One topic\nSummary ([Outlet](https://example.com/a))",
      highlights: [{ title: "A", link: "https://example.com/a", source: "Outlet", published: "2026-10-20T10:00:00+00:00", smart_groups: [], curated: false }],
    };
    const fetchMock = serve(report);
    const first = renderPage();
    expect(await screen.findByRole("heading", { level: 3, name: "One topic" })).toBeInTheDocument();
    first.unmount();
    renderPage();
    expect(await screen.findByRole("heading", { level: 3, name: "One topic" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("drops future-dated highlights and says so when none remain", async () => {
    serve({
      generated_at: "2026-10-21T01:40:00Z", analysis_date: "2026-10-20", model: "m", window_hours: 24,
      source_file: "", total_items_in_window_all: 1, total_items_in_window_curated: 0,
      daily_report_markdown: "### One topic\nSummary ([Outlet](https://example.com/a))",
      highlights: [{ title: "Later", link: "https://example.com/later", source: "Outlet", published: "2999-01-01T00:00:00+00:00", smart_groups: [], curated: false }],
    });
    const { container } = renderPage();
    expect(await screen.findByText("No curated highlights were generated for this window.")).toBeInTheDocument();
    expect(hrefs(container)).not.toContain("https://example.com/later");
    expect(hrefs(container)).toContain("https://example.com/a");
  });

  it("shows the unavailable state when no report can be loaded", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not found", { status: 404 })));
    renderPage();
    expect(await screen.findByText("Daily report is unavailable right now.")).toBeInTheDocument();
    expect(screen.queryByText(/Briefing for/)).not.toBeInTheDocument();
  });
});
