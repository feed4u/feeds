"""Host-runnable web checks via the repository's declared unittest check.

Run declared `test` with args: -s core/web/tests -v
Requires npm ci in core/web and npx playwright install chromium there.
"""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


WEB = Path(__file__).resolve().parents[1]


class TopicsVerification(unittest.TestCase):
    def test_web_suite(self):
        subprocess.run(
            ["npm", "test", "--", "--no-cache"], cwd=WEB,
            check=True, timeout=90,
        )

    def test_old_labels_are_rejected(self):
        # Mutate an isolated copy, never the candidate being reviewed.
        with tempfile.TemporaryDirectory(prefix="topics-regression-") as temp:
            copy = Path(temp) / "web"
            shutil.copytree(
                WEB, copy,
                ignore=shutil.ignore_patterns("node_modules", "dist", "public", "__pycache__"),
            )
            (copy / "node_modules").symlink_to(WEB / "node_modules", target_is_directory=True)
            page = copy / "src/pages/Topics.tsx"
            source = page.read_text()
            original = 'const heading = day ? `Topics for ${day}` : "Topics";'
            self.assertIn(original, source)
            page.write_text(source.replace(original, 'const heading = "Today\'s topics";'))
            report = Path(temp) / "vitest.json"
            result = subprocess.run(
                ["npm", "test", "--", "src/pages/Topics.test.tsx", "--no-cache",
                 "--reporter=json", f"--outputFile={report}"],
                cwd=copy, timeout=90,
            )
            self.assertEqual(result.returncode, 1)
            # A startup failure is not evidence that assertions rejected the labels.
            results = json.loads(report.read_text())
            self.assertEqual(results["numTotalTests"], 4)
            self.assertEqual(results["numFailedTests"], 4)
            for suite in results["testResults"]:
                for assertion in suite["assertionResults"]:
                    self.assertEqual(assertion["status"], "failed")
                    print(f"Old labels rejected: {assertion['fullName']}", flush=True)

    def test_live_digest_build_and_reload(self):
        subprocess.run(
            ["node", "scripts/verify-topics-live.mjs"], cwd=WEB,
            check=True, timeout=120,
        )
