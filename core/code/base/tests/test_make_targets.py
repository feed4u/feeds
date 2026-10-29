"""The root Makefile declares `lint` and `test`, and a failing step fails the target."""

import json
import os
import re
import subprocess
import tempfile
import unittest

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def make(*args):
    return subprocess.run(
        ["make", "--no-print-directory", "-C", ROOT, *args],
        capture_output=True, text=True, timeout=60,
    )


class DeclaredTargetsTest(unittest.TestCase):
    def test_lint_runs_python_and_web_checks(self):
        result = make("-n", "-W", "core/web/package-lock.json", "lint")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-m compileall -q core/code core/scripts", result.stdout)
        self.assertIn("cd core/web && npm ci", result.stdout)
        self.assertIn("cd core/web && npm run lint", result.stdout)

    def test_test_runs_python_and_web_suites(self):
        result = make("-n", "-W", "core/web/package-lock.json", "test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-m unittest discover -s core/code/base/tests -v", result.stdout)
        self.assertIn("cd core/web && npm ci", result.stdout)
        self.assertIn("cd core/web && npm test", result.stdout)


class WebSuiteTest(unittest.TestCase):
    def test_make_test_web_runs_vitest(self):
        # Installs core/web dependencies from the lock file first if missing.
        result = subprocess.run(
            ["make", "--no-print-directory", "-C", ROOT, "test-web"],
            capture_output=True, text=True, timeout=600,
        )
        # Vitest colours its summary on CI runners; match the text, not the escapes.
        output = ANSI_ESCAPE.sub("", result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("vitest run", output)
        self.assertRegex(output, r"Test Files\s+\d+ passed")
        print(output.strip().splitlines()[-4:], flush=True)


class ExitStatusTest(unittest.TestCase):
    def test_python_failure_fails_lint_and_test(self):
        for target in ("lint", "test"):
            with self.subTest(target=target):
                result = make(target, "PYTHON=false")
                self.assertNotEqual(result.returncode, 0)

    def test_web_failure_fails_lint_and_test(self):
        with tempfile.TemporaryDirectory(prefix="make-targets-") as web:
            scripts = {"lint": "exit 7", "test": "exit 7"}
            with open(os.path.join(web, "package.json"), "w") as fh:
                json.dump({"name": "failing-web", "private": True, "scripts": scripts}, fh)
            with open(os.path.join(web, "package-lock.json"), "w") as fh:
                fh.write("{}")
            # Dependencies already installed: the web step itself must fail.
            os.makedirs(os.path.join(web, "node_modules"))
            stamp = os.path.join(web, "node_modules", ".package-lock.json")
            with open(stamp, "w") as fh:
                fh.write("{}")
            os.utime(stamp, (2**31, 2**31))
            for target in ("lint-web", "test-web"):
                with self.subTest(target=target):
                    result = make(target, f"WEB={web}")
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn("exit 7", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
