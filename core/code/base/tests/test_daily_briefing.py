"""Tests for the daily briefing builder on a fixture day, using a fake LLM.

Run: python3 -m unittest discover -s core/code/base/tests -v
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import daily_briefing as db  # noqa: E402
from fake_llm_server import FakeLLMServer, unused_port_url  # noqa: E402
from llm_client import LLMClient, LLMConfig, LLMUnavailable  # noqa: E402

DAY = date(2026, 10, 12)
DAY_TS = int(datetime(2026, 10, 12, 12, tzinfo=timezone.utc).timestamp())


def make_item(n: int, **extra) -> dict:
    item = {
        "title": f"Story number {n} about topic {n % 7}",
        "summary": f"Summary for story {n}. " + "Detail " * 30,
        "link": f"https://example.com/article-{n}",
        "source": f"Outlet {n % 5} - A long feed description that should be trimmed",
        "published": "2026-10-12T12:00:00+00:00",
        "published_ts": DAY_TS - n,
        "smart_groups": ["Group A"],
        "curated": n % 3 == 0,
    }
    item.update(extra)
    return item


def write_fixture_day(archive: Path, count: int = 40) -> list:
    news = [make_item(n) for n in range(1, count + 1)]
    # Same story twice (same link) and a re-post under a new link (same title).
    news.append(dict(news[0]))
    news.append(make_item(1, link="https://mirror.example.org/copy-of-1"))
    blogs = [make_item(n) for n in range(1001, 1006)]
    for feed_type, rows in (("news", news), ("blog", blogs)):
        path = archive / feed_type / "daily" / f"{DAY.isoformat()}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"date": DAY.isoformat(), "items": rows}))
    # Another day, including a future-dated one, must never be read.
    for other in ("2026-10-11", "2026-12-03"):
        path = archive / "news" / "daily" / f"{other}.json"
        path.write_text(json.dumps({"items": [make_item(5000, link=f"https://other.example/{other}")]}))
    return [i["link"] for i in news[:count]] + [i["link"] for i in blogs]


def fake_editor(body: dict):
    """Behaves like a model: cites items it saw, plus some invented ids and URLs."""
    prompt = body["messages"][-1]["content"]
    if "Candidate stories" in prompt:
        ids = [int(x) for x in re.findall(r"^- \[([\d,]+)\]", prompt, re.M)[0].split(",")]
        all_ids = sorted({int(x) for group in re.findall(r"^- \[([\d,]+)\]", prompt, re.M)
                          for x in group.split(",")})
        return 200, {
            "headline": [
                {"text": "The day was dominated by topic stories.", "ids": ids},
                {"text": "An invented claim with no real source.", "ids": [99999]},
                {"text": "A claim with no ids at all."},
            ],
            "top_stories": [
                {"title": "Lead story", "summary": "See https://evil.example/phish for more.",
                 "ids": all_ids[:2]},
                {"title": "Made-up story", "summary": "Nothing supports this.", "ids": [424242]},
                {"title": "Second story", "summary": "Two outlets agree.", "ids": [str(all_ids[-1]), 0]},
            ],
        }
    seen = [int(x) for x in re.findall(r"^\[(\d+)\]", prompt, re.M)]
    return 200, "<think>pondering</think>" + json.dumps({
        "stories": [
            {"title": f"Chunk story {seen[0]}", "summary": "Factual sentence.", "ids": seen[:2]},
            {"title": "Hallucinated", "summary": "x", "ids": [seen[-1] + 100000]},
        ]
    })


def client_for(base_url: str) -> LLMClient:
    return LLMClient(LLMConfig(base_url=base_url, model="fake-model", timeout=10, retries=0), sleep=lambda s: None)


class ChunkingTests(unittest.TestCase):
    def test_chunks_stay_within_budget_and_keep_order(self):
        lines = [db.format_item_line(n, make_item(n)) for n in range(1, 301)]
        budget = 2000
        chunks = db.chunk_lines(lines, budget)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(sum(db.estimate_tokens(line) + 1 for line in chunk), budget)
        self.assertEqual([line for chunk in chunks for line in chunk], lines)

    def test_oversized_line_is_truncated_not_dropped(self):
        chunks = db.chunk_lines(["x" * 10_000, "short"], budget=100)
        self.assertEqual(len(chunks), 2)
        self.assertLessEqual(db.estimate_tokens(chunks[0][0]) + 1, 100)
        self.assertEqual(chunks[1], ["short"])

    def test_default_budget_fits_32k_lane(self):
        # Items budget + system prompt + instructions + 3000 output tokens < 32768.
        overhead = db.estimate_tokens(db.system_prompt("4u")) + db.estimate_tokens(
            db.reduce_prompt(DAY, [], 1000))
        self.assertLess(db.DEFAULT_TOKEN_BUDGET + overhead + 3000, 32_768)

    def test_builder_prompts_respect_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)
            write_fixture_day(archive, count=200)
            items = db.load_day_items(archive, DAY)
            with FakeLLMServer(fake_editor) as server:
                builder = db.BriefingBuilder(client_for(server.base_url), "4u", token_budget=1500)
                briefing, known, chunks = builder.build(DAY, items)
            self.assertGreater(chunks, 3)
            map_prompts = [r["messages"][-1]["content"] for r in server.requests
                           if "part " in r["messages"][-1]["content"]]
            self.assertEqual(len(map_prompts), chunks)
            for prompt in map_prompts:
                item_lines = [l for l in prompt.splitlines() if re.match(r"^\[\d+\]", l)]
                self.assertLessEqual(sum(db.estimate_tokens(l) + 1 for l in item_lines), 1500)
            # Every input item went to exactly one map call.
            cited = [int(m) for p in map_prompts for m in re.findall(r"^\[(\d+)\]", p, re.M)]
            self.assertEqual(sorted(cited), list(range(1, len(items) + 1)))


class InputTests(unittest.TestCase):
    def test_loads_only_the_day_and_dedupes(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)
            expected = write_fixture_day(archive)
            items = db.load_day_items(archive, DAY)
        links = [i["link"] for i in items]
        self.assertEqual(sorted(links), sorted(expected))  # dupes and other days gone
        self.assertNotIn("https://other.example/2026-12-03", links)

    def test_previous_utc_day(self):
        now = datetime(2026, 10, 14, 0, 30, tzinfo=timezone.utc)
        self.assertEqual(db.previous_utc_day(now), date(2026, 10, 13))

    def test_short_source(self):
        self.assertEqual(db.short_source("Engadget - Engadget is a web magazine"), "Engadget")
        self.assertEqual(db.short_source("https://www.awssecuritydigest.com/feed.xml"), "awssecuritydigest.com")

    def test_bullet_shows_at_most_four_links(self):
        known = {n: make_item(n) for n in range(1, 11)}
        briefing = {"headline": [], "top_stories": [{"title": "T", "summary": "", "ids": list(range(1, 11))}]}
        line = db.render_markdown(briefing, known).splitlines()[-1]
        self.assertEqual(len(re.findall(r"\]\(https://", line)), db.LINKS_PER_BULLET)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.archive = Path(self.tmp.name)
        self.input_links = set(write_fixture_day(self.archive))

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, base_url: str, now: datetime):
        return db.run(archive_dir=self.archive, vertical="k5", day=DAY,
                      client=client_for(base_url), now=now)

    def test_fixture_day_produces_expected_structure_with_traceable_links(self):
        with FakeLLMServer(fake_editor) as server:
            path = self._run(server.base_url, datetime(2026, 10, 13, 1, tzinfo=timezone.utc))
        self.assertEqual(path, self.archive / "daily_report_2026-10-12.json")
        report = json.loads(path.read_text())
        latest = json.loads((self.archive / "daily_report_latest.json").read_text())
        self.assertEqual(report, latest)

        # Fields the web page reads today.
        for key in ("generated_at", "analysis_date", "model", "window_hours",
                    "total_items_in_window_all", "total_items_in_window_curated",
                    "daily_report_markdown", "highlights"):
            self.assertIn(key, report)
        self.assertEqual(report["analysis_date"], "2026-10-12")
        self.assertEqual(report["vertical"], "k5")
        self.assertEqual(report["total_items_in_window_all"], len(self.input_links))

        md = report["daily_report_markdown"]
        self.assertTrue(md.startswith("### Headline summary"))
        self.assertIn("### Top stories", md)
        self.assertIn("- **Lead story**", md)

        # Nothing invented: every link anywhere in the report is an input item link.
        md_links = re.findall(r"\]\((https?://[^)]+)\)", md)
        self.assertTrue(md_links)
        self.assertTrue(set(md_links) <= self.input_links, set(md_links) - self.input_links)
        self.assertNotIn("evil.example", json.dumps(report))
        for story in report["top_stories"] + report["headline"]:
            self.assertTrue(story["links"])
            self.assertTrue(set(story["links"]) <= self.input_links)
        for hl in report["highlights"]:
            self.assertIn(hl["link"], self.input_links)
        self.assertTrue(report["highlights"])

        # Uncited / invented entries are dropped; every bullet carries a link.
        self.assertNotIn("Made-up story", md)
        self.assertNotIn("invented claim", md)
        self.assertNotIn("no ids at all", md)
        for line in md.splitlines():
            if line.startswith("- "):
                self.assertRegex(line, r"\]\(https://")
        self.assertEqual([s["title"] for s in report["top_stories"]], ["Lead story", "Second story"])

    def test_rerun_replaces_that_days_daily(self):
        with FakeLLMServer(fake_editor) as server:
            self._run(server.base_url, datetime(2026, 10, 13, 1, tzinfo=timezone.utc))
            self._run(server.base_url, datetime(2026, 10, 13, 5, tzinfo=timezone.utc))
        reports = sorted(p.name for p in self.archive.glob("daily_report_*.json"))
        self.assertEqual(reports, ["daily_report_2026-10-12.json", "daily_report_latest.json"])
        report = json.loads((self.archive / "daily_report_2026-10-12.json").read_text())
        self.assertEqual(report["generated_at"], "2026-10-13T05:00:00+00:00")

    def test_older_day_does_not_overwrite_newer_latest(self):
        latest = self.archive / "daily_report_latest.json"
        latest.write_text(json.dumps({"analysis_date": "2026-10-13"}))
        with FakeLLMServer(fake_editor) as server:
            self._run(server.base_url, datetime(2026, 10, 14, 1, tzinfo=timezone.utc))
        self.assertEqual(json.loads(latest.read_text()), {"analysis_date": "2026-10-13"})
        self.assertTrue((self.archive / "daily_report_2026-10-12.json").exists())

    def test_llm_down_writes_nothing(self):
        before = sorted(p.relative_to(self.archive) for p in self.archive.rglob("*"))
        with self.assertRaises(LLMUnavailable):
            self._run(unused_port_url(), datetime(2026, 10, 13, 1, tzinfo=timezone.utc))
        after = sorted(p.relative_to(self.archive) for p in self.archive.rglob("*"))
        self.assertEqual(before, after)

    def test_cli_skips_cleanly_when_llm_down(self):
        env = {"LLM_BASE_URL": unused_port_url(), "LLM_RETRIES": "0", "LLM_TIMEOUT": "2"}
        args = ["--vertical", "k5", "--archive-dir", str(self.archive), "--date", DAY.isoformat()]
        with mock.patch.dict(os.environ, env):
            self.assertEqual(db.main(args), 0)
            self.assertEqual(db.main(args + ["--strict"]), 2)
        self.assertEqual(list(self.archive.glob("daily_report_*.json")), [])

    def test_cli_builds_via_env_configured_endpoint(self):
        with FakeLLMServer(fake_editor) as server:
            env = {"LLM_BASE_URL": server.base_url, "LLM_MODEL": "fake-model"}
            args = ["--vertical", "4u", "--archive-dir", str(self.archive), "--date", DAY.isoformat()]
            with mock.patch.dict(os.environ, env):
                self.assertEqual(db.main(args), 0)
        report = json.loads((self.archive / "daily_report_2026-10-12.json").read_text())
        self.assertEqual(report["vertical"], "4u")
        self.assertEqual(report["model"], "fake-model")
        self.assertIn("AI and machine-learning", server.requests[0]["messages"][0]["content"])

    def test_cli_refuses_incomplete_day(self):
        today = datetime.now(timezone.utc).date().isoformat()
        args = ["--vertical", "k5", "--archive-dir", str(self.archive), "--date", today]
        self.assertEqual(db.main(args), 1)


if __name__ == "__main__":
    unittest.main()
