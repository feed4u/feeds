import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { TopicList, TOPICS_PAGE_SIZE } from "@/components/TopicList";
import { toTopicsDay } from "@/data/topicsData";
import { topicsFixture } from "@/test/topicsFixture";

describe("TopicList", () => {
  it("renders each topic with its title, summary and counts, in rank order", () => {
    render(<TopicList topics={toTopicsDay(topicsFixture()).topics} />);
    const topics = screen.getAllByTestId("topic");
    expect(topics).toHaveLength(2);
    expect(within(topics[0]).getByText("Microsoft patches exploited Exchange zero-day")).toBeInTheDocument();
    expect(within(topics[0]).getByText(/attackers already used/)).toBeInTheDocument();
    expect(within(topics[0]).getByText("3 stories · 3 sources")).toBeInTheDocument();
    expect(within(topics[1]).getByText("1 story · 1 source")).toBeInTheDocument();
  });

  it("expands a topic to its stories and collapses it again", () => {
    render(<TopicList topics={toTopicsDay(topicsFixture()).topics} />);
    const toggle = screen.getByRole("button", { name: /Exchange zero-day/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Emergency fix for Exchange flaw already used by hackers")).not.toBeInTheDocument();

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const links = screen.getAllByRole("link");
    expect(links.map((a) => a.getAttribute("href"))).toEqual([
      "https://news.example/1",
      "https://news.example/2",
      "https://news.example/3",
    ]);
    expect(screen.getByText("Emergency fix for Exchange flaw already used by hackers")).toBeInTheDocument();
    expect(screen.getByText("SecurityWeek")).toBeInTheDocument();

    fireEvent.click(toggle);
    expect(screen.queryAllByRole("link")).toHaveLength(0);
  });

  it("shows a page of topics at a time", () => {
    render(<TopicList topics={toTopicsDay(topicsFixture(40)).topics} />);
    expect(screen.getAllByTestId("topic")).toHaveLength(TOPICS_PAGE_SIZE);
    fireEvent.click(screen.getByRole("button", { name: /Show more topics \(12 left\)/ }));
    expect(screen.getAllByTestId("topic")).toHaveLength(42);
    expect(screen.queryByRole("button", { name: /Show more/ })).not.toBeInTheDocument();
  });

  it("says so when the day has no topics", () => {
    render(<TopicList topics={[]} />);
    expect(screen.getByText("No topics for this day.")).toBeInTheDocument();
  });
});

describe("toTopicsDay", () => {
  it("rejects an unknown schema version", () => {
    expect(() => toTopicsDay({ ...topicsFixture(), schema_version: 2 })).toThrow(/schema 2/);
  });
});
