#!/usr/bin/env python3
"""Show which daily briefing each site serves right now.

Usage: core/code/systemd/check_served_daily.py [SITE:VERTICAL ...]
Default: k5.ai:k5 4u.ai:4u. Exits 1 if a site cannot be read.
"""

import json
import sys
import urllib.request

DEFAULT_SITES = ["k5.ai:k5", "4u.ai:4u"]


def served_daily(site, vertical):
    url = f"https://{site}/data/{vertical}/archive/daily_report_latest.json"
    req = urllib.request.Request(url, headers={"User-Agent": "news-daily-check"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        report = json.load(resp)
    markdown = report.get("daily_report_markdown", "")
    return {
        "url": url,
        "analysis_date": report.get("analysis_date"),
        "generated_at": report.get("generated_at"),
        "model": report.get("model"),
        "links": markdown.count("](http"),
    }


def main(argv):
    failed = False
    for spec in argv or DEFAULT_SITES:
        site, _, vertical = spec.partition(":")
        try:
            print(json.dumps(served_daily(site, vertical or site.split(".")[0])))
        except Exception as exc:  # report every site, then fail
            print(f"{spec}: {exc}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
