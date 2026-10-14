import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HelmetProvider } from "react-helmet-async";
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

describe("Today's topics page", () => {
  it("loads the latest topics file and renders its topics", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(topicsFixture()), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderPage();

    expect(await screen.findByText("Microsoft patches exploited Exchange zero-day")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Today's topics" })).toBeInTheDocument();
    expect(screen.getByText(/4 stories from Monday, October 12 \(UTC\) in 2 topics, 1 reported more than once/))
      .toBeInTheDocument();
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/archive\/news\/topics\/topics_latest\.json$/);
  });

  it("explains when no topics file exists yet", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not found", { status: 404 })));
    renderPage();
    expect(await screen.findByText(/Topics are not available yet/)).toBeInTheDocument();
  });
});
