"""The PR/push gate workflow: triggers, path filter, read-only, scheduled workflow intact.

The workflow is parsed as text (standard library only). The path filter is
checked with a small matcher for the subset of GitHub's glob rules in use:
`*` matches within a path segment, `**` matches across segments.
"""

import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")


def read(name):
    with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as fh:
        return fh.read()


def glob_match(pattern, path):
    out = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.fullmatch(out, path) is not None


def ignore_patterns(text, event):
    """paths-ignore entries under `on.<event>`."""
    block = re.search(rf"^  {event}:\n((?:    .*\n|\n)*)", text, re.M)
    assert block, event
    body = block.group(1)
    m = re.search(r"^    paths-ignore:\n((?:      - .*\n)+)", body, re.M)
    assert m, f"no paths-ignore for {event}"
    return [re.sub(r'^      - "?(.*?)"?\s*$', r"\1", ln) for ln in m.group(1).splitlines()]


def runs(patterns, changed):
    """GitHub skips the run only when every changed file matches paths-ignore."""
    return any(not any(glob_match(p, f) for p in patterns) for f in changed)


class VerifyWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.text = read("verify.yml")

    def test_triggers_are_pr_and_push_to_main_only(self):
        self.assertRegex(self.text, r"(?m)^on:\n  pull_request:\n")
        self.assertRegex(self.text, r"(?m)^  push:\n    branches:\n      - main\n")
        self.assertNotRegex(self.text, r"(?m)^  (schedule|workflow_dispatch|pull_request_target):")

    def test_read_only_and_no_secrets(self):
        self.assertRegex(self.text, r"(?m)^permissions:\n  contents: read\n")
        self.assertNotIn("contents: write", self.text)
        self.assertNotIn("secrets.", self.text)
        self.assertNotIn("git push", self.text)
        self.assertNotIn("concurrency", self.text)

    def test_runs_declared_offline_checks_only(self):
        for cmd in ("run: make lint", "run: make test", "run: npm run build"):
            self.assertIn(cmd, self.text)
        self.assertRegex(self.text, r"working-directory: core/web\n\s+run: npm run build")
        for forbidden in ("fetch_news", "run_pipeline", "daily_briefing", "LLM_", "sync_web_data"):
            self.assertNotIn(forbidden, self.text)
        self.assertIn("actions/checkout@v4", self.text)
        self.assertIn("actions/setup-python@v5", self.text)
        self.assertIn("node-version-file: core/web/.nvmrc", self.text)
        self.assertTrue(os.path.exists(os.path.join(ROOT, "core/web/.nvmrc")))

    def test_path_filter(self):
        for event in ("pull_request", "push"):
            pats = ignore_patterns(self.text, event)
            with self.subTest(event=event):
                # Source changes run.
                for path in ("core/code/base/fetch_news.py", "core/web/src/App.tsx", "Makefile",
                             ".github/workflows/verify.yml", "core/source/4u/news.xml"):
                    self.assertTrue(runs(pats, [path]), path)
                # Generated-data-only changes do not.
                self.assertFalse(runs(pats, ["core/data/k5/latest.json"]))
                self.assertFalse(runs(pats, ["core/data/k5/archive/daily/2026-10-29.json",
                                             "core/data/4u/index.json"]))
                # Mixed commits run.
                self.assertTrue(runs(pats, ["core/data/k5/latest.json", "core/code/base/path_utils.py"]))
                # Near miss: a look-alike directory is not data.
                self.assertTrue(runs(pats, ["core/database/x.json"]))
                self.assertTrue(runs(pats, ["core/web/public/data/k5/latest.json"]))


class ScheduledWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.text = read("update_news_json.yml")

    def test_cadence_and_triggers_unchanged(self):
        self.assertIn('- cron: "23 */8 * * *"', self.text)
        self.assertRegex(self.text, r"(?m)^  workflow_dispatch:")
        self.assertRegex(self.text, r"(?m)^permissions:\n  contents: write\n")
        self.assertNotRegex(self.text, r"(?m)^  (push|pull_request):")

    def test_push_step_unchanged(self):
        self.assertIn("name: Commit and push data", self.text)
        self.assertIn("git push", self.text)
        self.assertIn("group: news-data", self.text)


class GlobMatcherTest(unittest.TestCase):
    def test_matcher_semantics(self):
        self.assertTrue(glob_match("core/data/**", "core/data/k5/a/b.json"))
        self.assertFalse(glob_match("core/data/**", "core/data"))
        self.assertTrue(glob_match("core/*/x", "core/a/x"))
        self.assertFalse(glob_match("core/*/x", "core/a/b/x"))


if __name__ == "__main__":
    unittest.main()
