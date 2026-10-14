#!/usr/bin/env python3
"""
build_daily_report.py - k5 daily briefing (kept for existing callers).

The briefing is built by the shared, provider-neutral builder in
core/code/base/daily_briefing.py, which talks to any OpenAI-compatible
endpoint (default: the local LLM lane). See that module for options.

    python core/code/k5/build_daily_report.py [--date YYYY-MM-DD]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "base"))

from daily_briefing import main  # noqa: E402

if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--vertical" not in argv:
        argv = ["--vertical", "k5", *argv]
    sys.exit(main(argv))
