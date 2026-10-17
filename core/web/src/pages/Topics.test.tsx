import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HelmetProvider } from "react-helmet-async";
import { vertical } from "@/config/verticals";
import Topics from "@/pages/Topics";
import { SearchProvider } from "@/contexts/SearchContext";
import { topicsFixture } from "@/test/topicsFixture";

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={client}>
        <MemoryRouter
          initialEntries={["/topics"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <SearchProvider>
            <Topics />
          </SearchProvider>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("Topics page", () => {
  it("loads the latest topics file and renders its topics", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(topicsFixture()), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderPage();

    expect(await screen.findByText("Microsoft patches exploited Exchange zero-day")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Topics for Monday, October 12" })).toBeInTheDocument();
    expect(screen.getByText(/4 stories from Monday, October 12 \(UTC\) in 2 topics, 1 reported more than once/))
      .toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe(`Topics for Monday, October 12 — ${vertical.metaTitle}`));
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/archive\/news\/topics\/topics_latest\.json$/);
  });

  it("uses the covered date even when generation happened on another day", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      ...topicsFixture(), date: "2026-10-16", generated_at: "2026-10-18T01:40:00Z",
    }))));
    renderPage();
    expect(await screen.findByRole("heading", { name: "Topics for Friday, October 16" })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe(`Topics for Friday, October 16 — ${vertical.metaTitle}`));
  });

  it("does not claim a day while loading", async () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));
    renderPage();
    expect(screen.getByRole("heading", { name: "Topics" })).toBeInTheDocument();
    expect(screen.getByText("Loading topics...")).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe(`Topics — ${vertical.metaTitle}`));
  });

  it("explains when no topics file exists yet", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not found", { status: 404 })));
    renderPage();
    expect(await screen.findByText(/Topics are not available yet/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Topics" })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe(`Topics — ${vertical.metaTitle}`));
  });
});
