"""The daily briefing user units run from their own clone, once a day."""

import configparser
import os
import unittest

SYSTEMD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "systemd")


def load(name):
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    with open(os.path.join(SYSTEMD_DIR, name)) as fh:
        parser.read_string(fh.read())
    return parser


class ServiceUnitTest(unittest.TestCase):
    def setUp(self):
        self.service = load("news-daily-briefing.service")["Service"]
        with open(os.path.join(SYSTEMD_DIR, "news-daily-briefing.service")) as fh:
            self.text = fh.read()

    def test_runs_from_dedicated_clone_not_a_working_checkout(self):
        self.assertIn("Environment=NEWS_DAILY_CLONE=%h/.cache/news-daily/news\n", self.text)
        self.assertEqual(
            self.service["ExecStart"],
            "/bin/bash ${NEWS_DAILY_CLONE}/core/code/run_daily_briefings.sh",
        )
        self.assertNotIn("/mnt/data1", self.text)

    def test_clones_on_first_start(self):
        self.assertIn('git clone --depth 1 --branch main "$NEWS_DAILY_REMOTE" "$NEWS_DAILY_CLONE"', self.text)
        self.assertIn("NEWS_DAILY_REMOTE=git@github.com:feed4u/feeds.git", self.text)


class TimerUnitTest(unittest.TestCase):
    def test_daily_after_the_midnight_data_run(self):
        timer = load("news-daily-briefing.timer")
        self.assertEqual(timer["Timer"]["OnCalendar"], "*-*-* 01:30:00 UTC")
        self.assertEqual(timer["Timer"]["Persistent"], "true")
        self.assertEqual(timer["Install"]["WantedBy"], "timers.target")


class CheckServedDailyTest(unittest.TestCase):
    def test_reports_served_date_and_links(self):
        import importlib.util
        import io
        import json
        from unittest import mock

        spec = importlib.util.spec_from_file_location(
            "check_served_daily", os.path.join(SYSTEMD_DIR, "check_served_daily.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        body = json.dumps({
            "analysis_date": "2026-10-13",
            "generated_at": "2026-10-14T07:20:30+00:00",
            "model": "qwen38-27b-mtp2:latest",
            "daily_report_markdown": "- a ([A](https://a.example)) b ([B](https://b.example))",
        }).encode()
        with mock.patch.object(module.urllib.request, "urlopen",
                               return_value=io.BytesIO(body)) as urlopen:
            info = module.served_daily("k5.ai", "k5")
        self.assertEqual(urlopen.call_args[0][0].full_url,
                         "https://k5.ai/data/k5/archive/daily_report_latest.json")
        self.assertEqual(info["analysis_date"], "2026-10-13")
        self.assertEqual(info["links"], 2)


if __name__ == "__main__":
    unittest.main()
