"""Tests for per-day topic grouping on a fixture day, using a fake LLM.

Run: python3 -m unittest discover -s core/code/base/tests -v
"""

from __future__ import annotations

import copy
import json
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

import build_topics as bt  # noqa: E402
from fake_llm_server import FakeLLMServer, static, unused_port_url  # noqa: E402
from llm_client import LLMClient, LLMConfig  # noqa: E402

DAY = date(2026, 10, 12)
DAY_TS = int(datetime(2026, 10, 12, 12, tzinfo=timezone.utc).timestamp())
NOW = datetime(2026, 10, 13, 1, 30, tzinfo=timezone.utc)

# (key, title, source, minutes after noon). Keys group the stories by event.
FIXTURE = [
    # One event told by four outlets with near-identical titles: rules link them.
    ("exch", "Microsoft patches Exchange Server zero-day exploited in attacks", "BleepingComputer", 0),
    ("exch", "Microsoft patches exploited Exchange Server zero-day in attacks", "SecurityWeek", 5),
    ("exch", "Exchange Server zero-day exploited in attacks, Microsoft patches", "The Record", 9),
    # Same event, different wording: rules miss it, the LLM should merge it.
    ("exch", "Emergency fix for Exchange flaw already used by hackers", "Dark Reading", 12),
    # Another event: rules link two tellings; a third telling is worded apart.
    ("lock", "LockBit ransomware gang claims attack on Dutch hospital chain", "The Record", 20),
    ("lock", "LockBit ransomware gang claims attack on hospital chain in Netherlands", "Cybernews", 25),
    ("lock", "Dutch hospitals hit by cyberattack, patient care disrupted", "NOS", 30),
    # Unrelated stories that share words with the events above: must stay apart.
    ("chrome", "Google releases Chrome 130 with new tab grouping features", "The Verge", 40),
    ("phish", "Phishing campaign impersonates Microsoft Teams support staff", "SecurityWeek", 50),
    ("sec", "SEC fines brokerage over missing cybersecurity disclosures", "Reuters", 60),
    ("sec", "SEC fines brokerage over missing cybersecurity disclosures (updated)", "Reuters", 61),  # same-feed repost
]


def make_item(index: int, key: str, title: str, source: str, minutes: int) -> dict:
    return {
        "title": title,
        "summary": f"{title}. Additional detail sentence number {index}. A third sentence.",
        "link": f"https://news.example/{key}/{index}",
        "source": source,
        "type": "news",
        "type_label": "News",
        "published": datetime.fromtimestamp(DAY_TS + minutes * 60, tz=timezone.utc).isoformat(),
        "published_ts": DAY_TS + minutes * 60,
        "smart_groups": ["Vulnerabilities"] if key == "exch" else [],
        "curated": key == "exch",
    }


FIXTURE_ITEMS = [make_item(i, *row) for i, row in enumerate(FIXTURE)]
KEY_OF = {item["link"]: row[0] for item, row in zip(FIXTURE_ITEMS, FIXTURE)}


def write_fixture_day(archive: Path, items=None) -> None:
    path = archive / "news" / "daily" / f"{DAY.isoformat()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"date": DAY.isoformat(), "items": items or FIXTURE_ITEMS}))


def numbers_by_key(prompt: str) -> dict:
    """Map event key -> story numbers as they appear in a batch prompt."""
    out: dict = {}
    for number, title in re.findall(r"^\s*\[(\d+)\] (.+?) \(", prompt, re.M):
        for item, row in zip(FIXTURE_ITEMS, FIXTURE):
            if item["title"] == title:
                out.setdefault(row[0], []).append(int(number))
    return out


def fake_grouper(body: dict):
    """Behaves like a careful model, plus a couple of the mistakes models make."""
    prompt = body["messages"][-1]["content"]
    if "separate batches" in prompt:  # cross-batch merge pass
        labels = dict(re.findall(r"^(T\d+): (.+?) \(\d+ stor", prompt, re.M))
        exch = [t for t, title in labels.items() if "Exchange" in title]
        return 200, {"merges": [{"ids": exch, "title": "Exchange zero-day patched",
                                 "summary": "Microsoft fixed an exploited Exchange flaw."}]}
    groups = numbers_by_key(prompt)
    topics = []
    if "exch" in groups:
        topics.append({"title": "Microsoft patches exploited Exchange zero-day",
                       "summary": "Microsoft fixed an Exchange Server flaw that attackers already used. "
                                  "See https://evil.example for more.",
                       "ids": groups["exch"] + [99999]})  # an invented story number
    if "lock" in groups:
        topics.append({"title": "LockBit hits Dutch hospital chain",
                       "summary": "LockBit claimed an attack that disrupted care at Dutch hospitals.",
                       "ids": groups["lock"]})
    if "exch" in groups and "lock" in groups:
        # Tries to put stories already placed in a topic into a second one.
        topics.append({"title": "Duplicate claim", "summary": "x", "ids": groups["lock"][:1] + groups["exch"][:1]})
    return 200, "<think>grouping</think>" + json.dumps({"topics": topics})


def client_for(base_url: str) -> LLMClient:
    return LLMClient(LLMConfig(base_url=base_url, model="fake-model", timeout=10, retries=0),
                     sleep=lambda s: None)


def groups_of(payload: dict) -> list:
    """Each topic as the sorted list of its stories' event keys."""
    return [sorted(KEY_OF[s["link"]] for s in t["stories"]) for t in payload["topics"]]


def build(archive: Path, server: FakeLLMServer, **kwargs) -> dict:
    path = bt.run(archive_dir=archive, vertical="k5", day=DAY, client=client_for(server.base_url),
                  now=NOW, **kwargs)
    return json.loads(path.read_text())


class FixtureDayClusteringTests(unittest.TestCase):
    def test_duplicates_merge_and_unrelated_stay_apart(self):
        with tempfile.TemporaryDirectory() as tmp, FakeLLMServer(fake_grouper) as server:
            archive = Path(tmp)
            write_fixture_day(archive)
            payload = build(archive, server)

        groups = groups_of(payload)
        # The four Exchange tellings (including the differently worded one) are one topic.
        self.assertIn(["exch"] * 4, groups)
        # The three LockBit tellings are one topic.
        self.assertIn(["lock"] * 3, groups)
        # The same-feed repost is merged by the rules.
        self.assertIn(["sec", "sec"], groups)
        # Unrelated stories are alone; no topic mixes events.
        self.assertIn(["chrome"], groups)
        self.assertIn(["phish"], groups)
        for group in groups:
            self.assertEqual(len(set(group)), 1, f"topic mixes events: {group}")
        self.assertEqual(payload["mode"], "llm")
        self.assertEqual(payload["stats"]["items"], len(FIXTURE_ITEMS))
        self.assertEqual(payload["stats"]["topics"], 5)
        self.assertEqual(payload["stats"]["singletons"], 2)
        self.assertGreaterEqual(payload["stats"]["topics_merging_candidates"], 2)

    def test_topics_are_ranked_by_sources_then_size(self):
        with tempfile.TemporaryDirectory() as tmp, FakeLLMServer(fake_grouper) as server:
            archive = Path(tmp)
            write_fixture_day(archive)
            payload = build(archive, server)
        topics = payload["topics"]
        self.assertEqual([t["rank"] for t in topics], list(range(1, len(topics) + 1)))
        self.assertEqual(topics[0]["title"], "Microsoft patches exploited Exchange zero-day")
        self.assertEqual(topics[0]["source_count"], 4)
        self.assertEqual(topics[1]["title"], "LockBit hits Dutch hospital chain")
        scores = [t["score"] for t in topics]
        self.assertEqual(scores, sorted(scores, reverse=True))
        # One source posting twice ranks below a singleton? No: 2*1+2 = 4 > 2*1+1 = 3.
        self.assertEqual(groups_of(payload)[2], ["sec", "sec"])

    def test_model_text_is_sanitised_and_singletons_keep_their_headline(self):
        with tempfile.TemporaryDirectory() as tmp, FakeLLMServer(fake_grouper) as server:
            archive = Path(tmp)
            write_fixture_day(archive)
            payload = build(archive, server)
        lead = payload["topics"][0]
        self.assertNotIn("http", lead["summary"])
        self.assertEqual(lead["origin"], "llm")
        chrome = next(t for t in payload["topics"] if groups_of({"topics": [t]})[0] == ["chrome"])
        self.assertEqual(chrome["title"], FIXTURE[7][1])
        self.assertEqual(chrome["origin"], "rules")
        # Summary of a rule topic is at most two sentences of the lead story.
        self.assertEqual(chrome["summary"].count(". "), 1)

    def test_split_batches_are_merged_across_batches(self):
        with tempfile.TemporaryDirectory() as tmp, FakeLLMServer(fake_grouper) as server:
            archive = Path(tmp)
            write_fixture_day(archive)
            # Three stories per batch: the Exchange tellings land in different batches.
            with mock.patch.object(bt, "SEND_ALL_BATCHES", 99):
                payload = build(archive, server, items_per_batch=3)
            self.assertGreater(payload["stats"]["batches"], 1)
            self.assertTrue(any("separate batches" in r["messages"][-1]["content"] for r in server.requests))
        self.assertIn(["exch"] * 4, groups_of(payload))
        self.assertEqual(payload["mode"], "llm")
        self.assertEqual(bt.validate_topics_payload(payload), [])

    def test_big_day_sends_only_related_stories(self):
        with tempfile.TemporaryDirectory() as tmp, FakeLLMServer(fake_grouper) as server:
            archive = Path(tmp)
            write_fixture_day(archive)
            with mock.patch.object(bt, "SEND_ALL_BATCHES", 0):
                payload = build(archive, server)
            sent = "\n".join(r["messages"][-1]["content"] for r in server.requests)
        # Unrelated single stories never reach the LLM and stay alone.
        self.assertNotIn("Chrome 130", sent)
        self.assertNotIn("Phishing campaign", sent)
        self.assertIn("Dutch hospitals hit", sent)  # shares "Dutch" and "hospital" with LockBit
        self.assertLess(payload["stats"]["stories_sent_to_llm"], len(FIXTURE_ITEMS))
        groups = groups_of(payload)
        self.assertIn(["lock"] * 3, groups)
        self.assertIn(["chrome"], groups)
        self.assertEqual(bt.validate_topics_payload(payload), [])

    def test_related_groups_match_inflected_words(self):
        items = [{"title": t, "link": str(i)} for i, t in enumerate([
            "Helsingin kaupunki nostaa kiinteistöveroa ensi vuonna",
            "Helsinki nostaa kiinteistöveron ensi vuodelle",
            "Tampereella avattiin uusi ratikkalinja",
        ])]
        groups = bt.related_groups([[0], [1], [2]], items)
        self.assertEqual(groups, [[[0], [1]], [[2]]])

    def test_prompts_respect_budget_and_batch_size(self):
        items = [make_item(i, f"k{i}", f"Unrelated headline number {i} about something", f"Outlet {i % 9}", i)
                 for i in range(500)]
        candidates = bt.rule_candidates(items)
        batches = bt.pack_batches(candidates, items, budget=3000, max_items=100)
        self.assertGreater(len(batches), 1)
        self.assertEqual(sorted(k for b in batches for m in b for k in m), list(range(500)))
        for batch in batches:
            lines = [line for m in batch for line in bt.format_candidate_block(m, items)]
            self.assertLessEqual(sum(bt.estimate_tokens(line) + 1 for line in lines), 3000)
            self.assertLessEqual(sum(len(m) for m in batch), 100)

    def test_default_budget_fits_32k_lane(self):
        overhead = bt.estimate_tokens(bt.SYSTEM_PROMPT) + bt.estimate_tokens(bt.batch_prompt(DAY, [], 1, 1))
        self.assertLess(bt.DEFAULT_TOKEN_BUDGET + overhead + bt.CHUNK_MAX_TOKENS, 32_768)


class FallbackTests(unittest.TestCase):
    def test_unreachable_llm_writes_rule_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)
            write_fixture_day(archive)
            path = bt.run(archive_dir=archive, vertical="k5", day=DAY, client=client_for(unused_port_url()), now=NOW)
            payload = json.loads(path.read_text())
        self.assertEqual(payload["mode"], "rules")
        self.assertEqual(bt.validate_topics_payload(payload), [])
        groups = groups_of(payload)
        self.assertIn(["exch"] * 3, groups)  # the rules alone link the three similar titles
        self.assertIn(["exch"], groups)       # but not the differently worded one
        for group in groups:
            self.assertEqual(len(set(group)), 1)

    def test_invalid_reply_keeps_rules_and_does_not_retry_hard(self):
        with tempfile.TemporaryDirectory() as tmp, FakeLLMServer(static("I cannot do that.")) as server:
            archive = Path(tmp)
            write_fixture_day(archive)
            payload = build(archive, server)
            self.assertEqual(len(server.requests), 1)
        self.assertEqual(payload["mode"], "rules")
        self.assertEqual(payload["stats"]["batches_failed"], 1)
        self.assertEqual(bt.validate_topics_payload(payload), [])

    def test_unavailable_llm_never_replaces_llm_topics(self):
        with tempfile.TemporaryDirectory() as tmp, FakeLLMServer(fake_grouper) as server:
            archive = Path(tmp)
            write_fixture_day(archive)
            first = build(archive, server)
            # New input arrives for the day, but the lane is down.
            write_fixture_day(archive, FIXTURE_ITEMS + [make_item(99, "new", "A new story", "Outlet", 90)])
            bt.run(archive_dir=archive, vertical="k5", day=DAY, client=client_for(unused_port_url()), now=NOW)
            kept = json.loads(bt.topics_path(archive, DAY).read_text())
        self.assertEqual(kept, first)

    def test_switched_off_vertical_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_fixture_day(Path(tmp) / "archive")
            original = dict(bt.TOPIC_VERTICALS)
            bt.TOPIC_VERTICALS["k5"] = False
            try:
                code = bt.main(["--vertical", "k5", "--archive-dir", str(Path(tmp) / "archive"),
                                "--date", DAY.isoformat()])
            finally:
                bt.TOPIC_VERTICALS.clear()
                bt.TOPIC_VERTICALS.update(original)
            self.assertEqual(code, 0)
            self.assertFalse((Path(tmp) / "archive" / "news" / "topics").exists())


class CliAndIdempotenceTests(unittest.TestCase):
    def test_cli_writes_valid_json_and_rerun_is_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "archive"
            write_fixture_day(archive)
            argv = ["--vertical", "k5", "--archive-dir", str(archive), "--date", DAY.isoformat(), "--rules-only"]
            self.assertEqual(bt.main(argv), 0)
            day_file = bt.topics_path(archive, DAY)
            latest = bt.topics_dir(archive) / "topics_latest.json"
            first, first_latest = day_file.read_bytes(), latest.read_bytes()
            self.assertEqual(first, first_latest)
            self.assertEqual(bt.validate_topics_payload(json.loads(first)), [])
            # Re-run, and a forced rebuild: same bytes (generated_at is not rewritten).
            self.assertEqual(bt.main(argv), 0)
            self.assertEqual(bt.main(argv + ["--force"]), 0)
            self.assertEqual(day_file.read_bytes(), first)
            self.assertEqual(latest.read_bytes(), first_latest)

    def test_llm_rerun_is_identical_and_skips_the_llm(self):
        with tempfile.TemporaryDirectory() as tmp, FakeLLMServer(fake_grouper) as server:
            archive = Path(tmp)
            write_fixture_day(archive)
            build(archive, server)
            first = bt.topics_path(archive, DAY).read_bytes()
            calls = len(server.requests)
            build(archive, server)  # input unchanged: no LLM call, file untouched
            self.assertEqual(len(server.requests), calls)
            self.assertEqual(bt.topics_path(archive, DAY).read_bytes(), first)
            build(archive, server, force=True)  # same answers: same bytes
            self.assertEqual(bt.topics_path(archive, DAY).read_bytes(), first)

    def test_older_day_does_not_replace_latest(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)
            write_fixture_day(archive)
            bt.run(archive_dir=archive, vertical="k5", day=DAY, client=None, now=NOW)
            older = archive / "news" / "daily" / "2026-10-11.json"
            older.write_text(json.dumps({"items": [make_item(1, "old", "Old story", "Outlet", -1440)]}))
            bt.run(archive_dir=archive, vertical="k5", day=date(2026, 10, 11), client=None, now=NOW)
            latest = json.loads((bt.topics_dir(archive) / "topics_latest.json").read_text())
        self.assertEqual(latest["date"], DAY.isoformat())


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp, FakeLLMServer(fake_grouper) as server:
            archive = Path(tmp)
            write_fixture_day(archive)
            cls.payload = build(archive, server)

    def test_written_payload_is_valid(self):
        self.assertEqual(bt.validate_topics_payload(self.payload), [])
        self.assertEqual(self.payload["schema_version"], bt.SCHEMA_VERSION)
        for key in ("vertical", "date", "generated_at", "mode", "model", "llm_endpoint",
                    "input_fingerprint", "stats", "topics"):
            self.assertIn(key, self.payload)
        story = self.payload["topics"][0]["stories"][0]
        for key in ("title", "summary", "link", "source", "feed_type", "published", "published_ts",
                    "smart_groups", "curated"):
            self.assertIn(key, story)

    def test_every_story_is_in_exactly_one_topic(self):
        links = [s["link"] for t in self.payload["topics"] for s in t["stories"]]
        self.assertEqual(sorted(links), sorted(i["link"] for i in FIXTURE_ITEMS))

    def assertInvalid(self, mutate, fragment):
        broken = copy.deepcopy(self.payload)
        mutate(broken)
        errors = bt.validate_topics_payload(broken)
        self.assertTrue(any(fragment in e for e in errors), f"{fragment!r} not in {errors}")

    def test_rejects_story_in_two_topics(self):
        self.assertInvalid(lambda p: p["topics"][1]["stories"].append(p["topics"][0]["stories"][0]),
                           "more than one topic")

    def test_rejects_wrong_rank_size_counts_and_version(self):
        self.assertInvalid(lambda p: p["topics"].reverse(), "rank")
        self.assertInvalid(lambda p: p["topics"][0].update(size=99), "size")
        self.assertInvalid(lambda p: p["stats"].update(singletons=0), "stats.singletons")
        self.assertInvalid(lambda p: p.update(schema_version=2), "schema_version")
        self.assertInvalid(lambda p: p.update(mode="magic"), "mode")
        self.assertInvalid(lambda p: p["topics"][0].update(title="  "), "empty title")
        self.assertInvalid(lambda p: p.pop("topics"), "topics")

    def test_write_refuses_invalid_payload(self):
        broken = copy.deepcopy(self.payload)
        broken["topics"][0]["size"] = 0
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                bt.write_outputs(Path(tmp), broken)
            self.assertFalse(bt.topics_dir(Path(tmp)).exists())


if __name__ == "__main__":
    unittest.main()
