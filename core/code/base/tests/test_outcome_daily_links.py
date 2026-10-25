"""Tests for the outcome scorer of the daily briefing's link/date integrity.

Every case runs the scorer the way the Agent Console does: a subprocess
(``python3 -I -B``) with only the AGENT_CONSOLE_OUTCOME_* variables, scoring a
checkout. Fixture days are written here; the real-day case reads the committed
4u archive and prints counts only.

Run: python3 -m unittest discover -s core/code/base/tests -v
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import py_compile
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
REPO = BASE.parents[2]
SCORER = BASE / "outcome_daily_links.py"
sys.path.insert(0, str(BASE))

import outcome_daily_links as odl  # noqa: E402
from build_topics import validate_topics_payload  # noqa: E402

DAY = "2026-10-12"
REAL_VERTICAL, REAL_DAY = "4u", "2026-10-20"
REAL_ARCHIVE = REPO / "core" / "data" / REAL_VERTICAL / "archive"

# One-line break in the scored checkout: items are numbered one off, so each
# section cites a neighbour's link instead of its topic's own stories.
OFF_BY_ONE = (
    'number_of = {item["link"]: n for n, item in known.items()}',
    'number_of = {item["link"]: n + 1 for n, item in known.items()}',
)
# The fixture day cites every item, so it needs a numbering that stays in range.
REVERSED = (OFF_BY_ONE[0], 'number_of = {item["link"]: len(known) + 1 - n for n, item in known.items()}')


def item(n: int, feed: str = "news", published: str = f"{DAY}T12:00:00+00:00", ts: int = 0) -> dict:
    return {
        "title": f"Fixture {feed} story {n} on subject {n % 4}",
        "summary": f"Summary of fixture {feed} story {n}.",
        "link": f"https://fixture.example/{feed}/{n}",
        "source": f"Outlet {n % 3} - fixture feed",
        "published": published,
        "published_ts": ts or 1791806400 - n * 60,  # 2026-10-12 12:00Z minus n minutes
        "smart_groups": [],
        "curated": False,
        "feed_type": feed,
    }


def write_fixture_archive(archive: Path) -> None:
    news = [item(n) for n in range(1, 13)]
    blog = [item(n, "blog") for n in range(1, 5)]
    for feed, rows in (("news", news), ("blog", blog)):
        path = archive / feed / "daily" / f"{DAY}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"date": DAY, "items": rows}))
    topics = []
    for t in range(1, 5):
        stories = [news[(t - 1) * 3 + k] for k in range(3)] + [blog[t - 1]]
        topics.append({
            "id": f"{DAY}-t{t}", "rank": t, "title": f"Fixture topic {t}", "summary": f"Topic {t} summary.",
            "size": len(stories), "source_count": 3, "sources": ["Outlet 0", "Outlet 1", "Outlet 2"],
            "score": 10 - t, "first_ts": 0, "latest_ts": 0, "origin": "rules", "stories": stories,
        })
    payload = {
        "schema_version": 1, "date": DAY, "vertical": "4u", "generated_at": f"{DAY}T23:00:00+00:00",
        "mode": "rules", "model": None, "llm_endpoint": None, "input_fingerprint": "fixture",
        "stats": {"items": 16, "topics": 4, "multi_story_topics": 4, "singletons": 0,
                  "largest_topic": 4, "llm_calls": 0},
        "topics": topics,
    }
    assert validate_topics_payload(payload) == [], validate_topics_payload(payload)
    path = archive / "news" / "topics" / f"{DAY}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_state(root: Path) -> list:
    return sorted((p.relative_to(root).as_posix(), p.stat().st_mtime_ns) for p in root.rglob("*"))


def make_checkout(root: Path, scorer_source: str = None, replace: tuple = None) -> Path:
    """A copy of core/code/base at root, optionally with one line changed."""
    base = root / "core" / "code" / "base"
    shutil.copytree(BASE, base, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
    if scorer_source is not None:
        (base / "outcome_daily_links.py").write_text(scorer_source)
    if replace is not None:
        target = base / "daily_briefing.py"
        text = target.read_text()
        assert text.count(replace[0]) == 1, f"mutation anchor not unique: {replace[0]}"
        target.write_text(text.replace(replace[0], replace[1]))
    return root.resolve()


class ScorerHarness(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="odl-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.private = self.tmp / "private"
        self.scratch = self.private / ".outcome-scratch-1"
        self.scratch.mkdir(parents=True)

    def freeze_fixture(self, out_name: str = "day") -> Path:
        archive = self.tmp / "archive"
        write_fixture_archive(archive)
        out = self.private / out_name
        odl.freeze(archive, "4u", odl._day(DAY), out, "fixture")
        return out

    def env(self, frozen: Path, checkout: Path = REPO, **over: str) -> dict:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "AGENT_CONSOLE_OUTCOME_INPUT": str(frozen / "input.json"),
            "AGENT_CONSOLE_OUTCOME_REFERENCE": str(frozen / "reference.json"),
            "AGENT_CONSOLE_OUTCOME_CHECKOUT": str(checkout),
            "AGENT_CONSOLE_OUTCOME_SCRATCH": str(self.scratch),
        }
        env.update(over)
        return {k: v for k, v in env.items() if v is not None}

    def run_scorer(self, env: dict, scorer: Path = SCORER, args: tuple = (), cwd: Path = None):
        return subprocess.run(
            [sys.executable, "-I", "-B", str(scorer), *args],
            env=env, cwd=str(cwd or self.tmp), capture_output=True, text=True, timeout=300,
        )

    def score_of(self, result) -> dict:
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        return json.loads(result.stdout)

    def rewrite(self, path: Path, change) -> None:
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data))


class FixtureDayTest(ScorerHarness):
    def test_fixture_day_scores_one_and_prints_only_the_score(self):
        frozen = self.freeze_fixture()
        result = self.run_scorer(self.env(frozen))
        score = self.score_of(result)
        self.assertEqual(set(score), {"score", "items"})
        self.assertEqual(score["score"], 1.0)
        self.assertGreater(score["items"], 0)
        self.assertEqual(result.stdout.strip().count("\n"), 0)

    def test_scored_checkout_stays_clean_and_inputs_byte_identical(self):
        frozen = self.freeze_fixture()
        checkout = make_checkout(self.tmp / "checkout")
        before = tree_state(checkout)
        hashes = (sha(frozen / "input.json"), sha(frozen / "reference.json"))
        self.score_of(self.run_scorer(self.env(frozen, checkout)))
        self.assertEqual(tree_state(checkout), before)
        self.assertEqual((sha(frozen / "input.json"), sha(frozen / "reference.json")), hashes)

    def test_broken_checkout_lowers_fixture_score(self):
        frozen = self.freeze_fixture()
        broken = make_checkout(self.tmp / "broken", replace=REVERSED)
        score = self.score_of(self.run_scorer(self.env(frozen, broken)))
        self.assertLess(score["score"], 1.0)

    def test_reference_on_another_day_fails(self):
        frozen = self.freeze_fixture()
        self.rewrite(frozen / "reference.json", lambda d: d["links"].update(
            {k: "2026-10-11" for k in list(d["links"])[:3]}))
        score = self.score_of(self.run_scorer(self.env(frozen)))
        self.assertLess(score["score"], 1.0)

    def test_link_missing_from_reference_fails(self):
        frozen = self.freeze_fixture()
        self.rewrite(frozen / "reference.json", lambda d: d["links"].pop("https://fixture.example/news/1"))
        score = self.score_of(self.run_scorer(self.env(frozen)))
        self.assertLess(score["score"], 1.0)

    def test_scorer_is_offline(self):
        frozen = self.freeze_fixture()
        env = self.env(frozen)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network used")), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = odl.main([], env)
        self.assertEqual(code, 0, err.getvalue()[-2000:])
        self.assertEqual(json.loads(out.getvalue())["score"], 1.0)


class ScoringRulesTest(unittest.TestCase):
    """score_report against hand-built reports: what passes and what must not."""

    LINK = "https://fixture.example/news/1"
    OTHER = "https://fixture.example/news/2"

    def bundle(self):
        return {"date": DAY, "topics": {"topics": [{"id": "t1", "stories": [{"link": self.LINK}]}]}}

    def report(self, published=f"{DAY}T12:00:00+00:00", link=LINK, md_link=LINK):
        return {
            "headline": [],
            "top_stories": [{"title": "T", "summary": "", "links": [link], "topic_id": "t1"}],
            "daily_report_markdown": f"### T\n([Outlet]({md_link}))",
            "highlights": [{"link": link, "published": published}],
        }

    def test_exact_report_passes(self):
        ref = {self.LINK: DAY, self.OTHER: DAY}
        self.assertEqual(odl.score_report(self.report(), self.bundle(), ref), (3, 3))

    def test_near_miss_dates(self):
        ref = {self.LINK: DAY}
        # Same UTC day through another offset: must pass.
        self.assertEqual(odl.score_report(self.report("2026-10-13T01:00:00+02:00"), self.bundle(), ref)[0], 3)
        # Same wall-clock day but the next UTC day: must not.
        self.assertEqual(odl.score_report(self.report("2026-10-12T23:30:00-02:00"), self.bundle(), ref)[0], 2)
        # No offset: the UTC day is unknown, so it must not pass.
        self.assertEqual(odl.score_report(self.report("2026-10-12T12:00:00"), self.bundle(), ref)[0], 2)

    def test_sourced_link_outside_its_topic_fails(self):
        ref = {self.LINK: DAY, self.OTHER: DAY}
        # The section and its markdown fail; the highlight of what they cite is
        # still a correctly dated, cited source link.
        self.assertEqual(odl.score_report(self.report(link=self.OTHER, md_link=self.OTHER), self.bundle(), ref), (1, 3))

    def test_non_http_and_markdown_escaping(self):
        ref = {"javascript:alert(1)": DAY}
        bundle = {"date": DAY, "topics": {"topics": [{"id": "t1", "stories": [{"link": "javascript:alert(1)"}]}]}}
        self.assertEqual(odl.score_report(self.report(link="javascript:alert(1)", md_link="x"), bundle, ref)[0], 0)
        paren = "https://fixture.example/a_(b)"
        bundle = {"date": DAY, "topics": {"topics": [{"id": "t1", "stories": [{"link": paren}]}]}}
        report = self.report(link=paren, md_link="https://fixture.example/a_(b%29")
        self.assertEqual(odl.score_report(report, bundle, {paren: DAY}), (3, 3))

    def test_highlight_not_cited_fails(self):
        ref = {self.LINK: DAY, self.OTHER: DAY}
        report = self.report()
        report["highlights"].append({"link": self.OTHER, "published": f"{DAY}T01:00:00Z"})
        self.assertEqual(odl.score_report(report, self.bundle(), ref), (3, 4))


@unittest.skipUnless((REAL_ARCHIVE / "news" / "topics" / f"{REAL_DAY}.json").is_file(), "real day not in checkout")
class RealDayTest(ScorerHarness):
    """The committed 4u 2026-10-20 day: real positive and a broken-checkout control."""

    def test_real_day_positive_and_broken_checkout_control(self):
        frozen = self.private / "real"
        manifest = odl.freeze(REAL_ARCHIVE, REAL_VERTICAL, odl._day(REAL_DAY), frozen, "test")
        self.assertGreater(manifest["reference_links"], 100)
        hashes = (sha(frozen / "input.json"), sha(frozen / "reference.json"))
        self.assertEqual(hashes, (manifest["input_sha256"], manifest["reference_sha256"]))

        real = self.score_of(self.run_scorer(self.env(frozen)))
        self.assertEqual(real["score"], 1.0)
        self.assertGreater(real["items"], 20)

        broken = make_checkout(self.tmp / "broken", replace=OFF_BY_ONE)
        lowered = self.score_of(self.run_scorer(self.env(frozen, broken)))
        self.assertLess(lowered["score"], real["score"])
        self.assertEqual((sha(frozen / "input.json"), sha(frozen / "reference.json")), hashes)
        print(f"\n[real 4u {REAL_DAY}] score {real['score']} on {real['items']} items; "
              f"broken checkout {lowered['score']} on {lowered['items']} items")


# --------------------------------------------------------------------------- #
# Guards: each refuses its case, and with only that guard removed it does not.
# --------------------------------------------------------------------------- #

GUARD_LINE = re.compile(r"^(?P<indent>[ \t]*)(?P<stmt>\S.*?)[ \t]+# guard: (?P<name>[a-z-]+)$", re.MULTILINE)


def without_guard(name: str) -> str:
    source = SCORER.read_text()
    matches = [m for m in GUARD_LINE.finditer(source) if m.group("name") == name]
    assert len(matches) == 1, name
    m = matches[0]
    return source[: m.start()] + f"{m.group('indent')}pass  # guard removed: {name}" + source[m.end():]


class GuardTest(ScorerHarness):
    """Each case: (setup -> (env, cwd, args), exit code, stderr text, what happens without the guard)."""

    def case(self, name: str, checkout: Path):
        frozen = self.freeze_fixture()
        env = self.env(frozen, checkout)
        cwd, args, escaped = None, (), None
        if name == "env-missing":
            env.pop("AGENT_CONSOLE_OUTCOME_INPUT")
        elif name == "path-relative":
            env["AGENT_CONSOLE_OUTCOME_INPUT"] = "input.json"
            env["AGENT_CONSOLE_OUTCOME_REFERENCE"] = "reference.json"
            cwd = frozen
        elif name == "path-traversal":
            env["AGENT_CONSOLE_OUTCOME_INPUT"] = str(frozen / ".." / frozen.name / "input.json")
            env["AGENT_CONSOLE_OUTCOME_REFERENCE"] = str(frozen / ".." / frozen.name / "reference.json")
        elif name == "path-symlink":
            link = self.private / "linked"
            link.symlink_to(frozen, target_is_directory=True)
            env["AGENT_CONSOLE_OUTCOME_INPUT"] = str(link / "input.json")
            env["AGENT_CONSOLE_OUTCOME_REFERENCE"] = str(link / "reference.json")
        elif name == "path-foreign":
            other = self.private / "other"
            other.mkdir()
            shutil.copy(frozen / "reference.json", other / "reference.json")
            env["AGENT_CONSOLE_OUTCOME_REFERENCE"] = str(other / "reference.json")
        elif name == "path-in-checkout":
            inside = checkout / "core" / "data-copy"
            shutil.copytree(frozen, inside)
            env["AGENT_CONSOLE_OUTCOME_INPUT"] = str(inside / "input.json")
            env["AGENT_CONSOLE_OUTCOME_REFERENCE"] = str(inside / "reference.json")
        elif name == "scratch-dir":
            bogus = self.private / "scratch-file"
            bogus.write_text("")
            env["AGENT_CONSOLE_OUTCOME_SCRATCH"] = str(bogus)
        elif name == "checkout-path":
            env["AGENT_CONSOLE_OUTCOME_CHECKOUT"] = "."
            cwd = checkout
        elif name == "checkout-code":
            env["AGENT_CONSOLE_OUTCOME_CHECKOUT"] = str(self.tmp)
        elif name == "unreadable":
            (frozen / "input.json").write_text("{not json")
        elif name == "bad-day":
            self.rewrite(frozen / "input.json", lambda d: d.update(date="2026-13-45"))
            self.rewrite(frozen / "reference.json", lambda d: d.update(date="2026-13-45"))
        elif name == "input-format":
            self.rewrite(frozen / "input.json", lambda d: d.update(format="something-else/9"))
        elif name == "input-daily":
            self.rewrite(frozen / "input.json", lambda d: d.update(daily={}))
        elif name == "input-topics":
            self.rewrite(frozen / "input.json", lambda d: d.update(topics=None))
        elif name == "member-name":
            escaped = self.tmp / "escaped"
            self.rewrite(frozen / "input.json", lambda d: d["daily"].update({str(escaped): d["daily"]["blog"]}))
            escaped = escaped / "daily" / f"{DAY}.json"
        elif name == "reference-format":
            self.rewrite(frozen / "reference.json", lambda d: d.pop("links"))
        elif name == "reference-foreign":
            self.rewrite(frozen / "reference.json", lambda d: d.update(
                date="2026-10-11", links={k: "2026-10-11" for k in d["links"]}))
        elif name in ("scored-crash", "output-missing", "output-not-json", "output-malformed", "no-links"):
            pass  # these break the scored checkout instead; see CHECKOUT_BREAKS
        elif name.startswith("freeze-"):
            archive = self.tmp / "archive"
            out = {"freeze-into-checkout": checkout / "core" / "frozen-here",
                   "freeze-overwrite": frozen,
                   "freeze-empty": self.private / "empty"}[name]
            day = "2026-01-01" if name == "freeze-empty" else DAY
            args = ("freeze", "--vertical", "4u", "--date", day, "--archive-dir", str(archive), "--out", str(out))
            escaped = out / "input.json"
            if name == "freeze-overwrite":
                escaped.write_text("an earlier frozen input\n")
        return env, cwd, args, escaped

    CHECKOUT_BREAKS = {
        "scored-crash": ('known = {n: item for n, item in enumerate(items, start=1)}\n        number_of',
                         'known = {}\n        number_of'),
        "output-missing": ('daily_path.write_text(text, encoding="utf-8")', 'pass'),
        "output-not-json": ('text = json.dumps(payload, indent=2, ensure_ascii=False) + "\\n"',
                            'text = "not json"'),
        "output-malformed": ('text = json.dumps(payload, indent=2, ensure_ascii=False) + "\\n"',
                             'text = json.dumps([payload])'),
        "no-links": ('"highlights": [to_highlight(item) for item in cited_items(briefing, known)[:HIGHLIGHT_LIMIT]],',
                     '"highlights": [], "top_stories": [], "daily_report_markdown": "",'),
    }

    EXPECT = {
        # name: (exit code with the guard, stderr text, without the guard: "scores" | "escapes" | "other")
        "env-missing": (2, "is not set", "other"),
        "path-relative": (2, "is not absolute", "scores"),
        "path-traversal": (2, "traverses upwards", "scores"),
        "path-symlink": (2, "goes through a symlink", "scores"),
        "path-foreign": (2, "not frozen beside its input", "scores"),
        "path-in-checkout": (2, "inside the scored checkout", "scores"),
        "scratch-dir": (2, "scratch is not a directory", "other"),
        "checkout-path": (2, "checkout is not an absolute path", "scores"),
        "checkout-code": (2, "checkout has no daily_briefing.py", "other"),
        "unreadable": (2, "input is unreadable", "other"),
        "bad-day": (2, "not a day", "other"),
        "input-format": (2, "not a daily-links input", "scores"),
        "input-daily": (2, "input has no daily files", "other"),
        "input-topics": (2, "input has no topics", "other"),
        "member-name": (2, "unsafe feed type", "escapes"),
        "reference-format": (2, "not a daily-links reference", "other"),
        "reference-foreign": (2, "another vertical or day", "scores"),
        "scored-crash": (4, "the scored checkout failed", "other"),
        "output-missing": (4, "wrote no report", "other"),
        "output-not-json": (4, "the report is not JSON", "other"),
        "output-malformed": (4, "the report is not an object", "other"),
        "no-links": (4, "the report emitted no links", "scores"),
        "freeze-into-checkout": (2, "refusing to freeze into the checkout", "escapes"),
        "freeze-overwrite": (2, "refusing to overwrite", "escapes"),
        "freeze-empty": (2, "no daily files and topics", "other"),
    }

    def test_every_guard_has_a_case(self):
        names = {m.group("name") for m in GUARD_LINE.finditer(SCORER.read_text())}
        self.assertEqual(names, set(self.EXPECT))

    def check_guard(self, name: str, removed: bool) -> None:
        source = without_guard(name) if removed else None
        root = self.tmp / ("without" if removed else "with")
        checkout = make_checkout(root, scorer_source=source, replace=self.CHECKOUT_BREAKS.get(name))
        scorer = checkout / "core" / "code" / "base" / "outcome_daily_links.py"
        py_compile.compile(str(scorer), cfile=str(self.tmp / f"{name}.pyc"), doraise=True)
        env, cwd, args, escaped = self.case(name, checkout)
        before = escaped.read_bytes() if escaped is not None and escaped.exists() else None
        result = self.run_scorer(env, scorer=scorer, args=args, cwd=cwd)
        code, text, without = self.EXPECT[name]
        if not removed:
            self.assertEqual(result.returncode, code, result.stderr[-2000:])
            self.assertIn(text, result.stderr)
            self.assertEqual(result.stdout, "")
            if escaped is not None:
                after = escaped.read_bytes() if escaped.exists() else None
                self.assertEqual(after, before, "a refused case still wrote")
            return
        self.assertNotIn(text, result.stderr)
        if without == "scores":
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
            json.loads(result.stdout)
        elif without == "escapes":
            self.assertTrue(escaped.exists())
            self.assertNotEqual(escaped.read_bytes(), before)
        else:
            # A later check or a raw crash: never this guard's own answer.
            self.assertNotEqual(result.returncode, 0)


def _add_guard_tests() -> None:
    for name in GuardTest.EXPECT:
        slug = name.replace("-", "_")
        setattr(GuardTest, f"test_guard_{slug}", lambda self, n=name: self.check_guard(n, removed=False))
        setattr(GuardTest, f"test_removed_guard_{slug}", lambda self, n=name: self.check_guard(n, removed=True))


_add_guard_tests()


if __name__ == "__main__":
    unittest.main()
