#!/usr/bin/env python3
"""
build_daily_report.py

Generate a SOC-ready daily briefing from curated items in data/news_recent.json.
The script:
    1. Loads the latest news cache.
    2. Filters items within a configurable hourly window.
    3. Keeps curated items only (falling back to all items if none curated).
    4. Builds a formatted context list.
    5. Calls the OpenAI Responses API for a structured markdown briefing.
    6. Saves JSON outputs (dated + latest) for /morning-call to consume.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI, APIError


# --------------------------------------------------------------------------- #
# Configuration (env vars allow customization per environment or workflow)
# --------------------------------------------------------------------------- #

NEWS_RECENT_PATH = Path(os.environ.get("NEWS_JSON_PATH", "data/news_recent.json"))
WINDOW_HOURS = int(os.environ.get("DAILY_REPORT_WINDOW_HOURS", "24"))
MAX_ITEMS_FOR_CONTEXT = int(os.environ.get("DAILY_REPORT_MAX_ITEMS", "100"))
OPENAI_MODEL = os.environ.get("DAILY_REPORT_MODEL", "gpt-4o-mini")
OUTPUT_DIR = Path(os.environ.get("DAILY_REPORT_OUTPUT_DIR", "data/archive"))
MAX_OUTPUT_TOKENS = int(os.environ.get("DAILY_REPORT_MAX_OUTPUT_TOKENS", "3000"))


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def load_news_recent(path: Path) -> Dict[str, Any]:
    """Load the latest news cache."""
    if not path.exists():
        raise FileNotFoundError(f"news_recent.json not found at {path}")

    print(f"[INFO] Loading {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "items" not in data:
        raise ValueError("news_recent.json must be a dict with an 'items' list")

    print(f"[INFO] Loaded {len(data['items'])} items")
    return data


def filter_last_hours(items: List[Dict[str, Any]], hours: int) -> List[Dict[str, Any]]:
    """Return items published within the last N hours (sorted newest first)."""
    cutoff = int(time.time()) - hours * 3600
    filtered = []
    for itm in items:
        ts = itm.get("published_ts")
        if isinstance(ts, (int, float)) and ts >= cutoff:
            itm["_published_ts"] = int(ts)
            filtered.append(itm)

    filtered.sort(key=lambda x: x["_published_ts"], reverse=True)
    print(f"[INFO] Items within last {hours}h: {len(filtered)}")
    return filtered


def filter_curated(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep curated items only; preserves order."""
    curated = [itm for itm in items if bool(itm.get("curated"))]
    print(f"[INFO] Curated items in window: {len(curated)}")
    return curated


def build_context_snippet(items: List[Dict[str, Any]]) -> str:
    """
    Turn curated items into a rich text block for the LLM.
    Each entry uses timestamps, sources, titles, tags, and links.
    """
    lines: List[str] = []
    for idx, itm in enumerate(items, start=1):
        ts = itm.get("_published_ts") or itm.get("published_ts")
        if isinstance(ts, (int, float)):
            published = datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%SZ"
            )
        else:
            published = itm.get("published") or "N/A"

        source = itm.get("source") or "Unknown"
        title = itm.get("title") or "(no title)"
        link = itm.get("link") or "N/A"
        groups = itm.get("smart_groups") or []
        tags = ", ".join(groups[:5]) if isinstance(groups, list) else str(groups)

        lines.append(
            f"[{idx}] {published} | {source} | {title}\n"
            f"    Link: {link}\n"
            f"    Tags: {tags}"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Prompt builders
# --------------------------------------------------------------------------- #

def build_system_prompt() -> str:
    """Persona + tone instructions for the LLM."""
    return (
        "You are a seasoned cybersecurity consultant and threat intelligence lead supporting a 24/7 SOC.\n"
        "You excel at:\n"
        "- Triage of high-signal news and mapping to SOC priorities.\n"
        "- Translating external intelligence into concrete guidance for incident responders.\n"
        "- Communicating concisely for shift handovers.\n\n"
        "Objective: Based on the last 24 hours of curated security news, produce a short, highly actionable daily briefing for the SOC.\n"
        "Prioritize:\n"
        "- Live or active threats (exploited CVEs, ongoing campaigns, ransomware leaks, supply-chain incidents, critical vendor advisories).\n"
        "- Clear monitoring/detection/hardening advice linked to the stories.\n"
        "- Brevity and clarity (600–900 words; short bullets).\n"
    )


def build_user_prompt(context_snippet: str, hours: int, curated_count: int) -> str:
    """Task instructions and formatting constraints."""
    return (
        f"The following curated items were collected during the last {hours} hours "
        f"(total curated items in this window: {curated_count}).\n\n"
        "CONTEXT:\n"
        "------------------------------------------------------------\n"
        f"{context_snippet}\n"
        "------------------------------------------------------------\n\n"
        "TASK:\n"
        "Write a markdown daily briefing for SOC L1–L3 analysts with:\n"
        "1. `### Executive Summary` – up to three bullets calling out critical developments.\n"
        "2. `### High-priority items (immediate attention)` – focus on top 3–5 issues. "
        "For each, provide three sub-bullets covering what happened, why it matters, and immediate SOC actions.\n"
        "3. `### Monitoring & detection recommendations` – 5–8 bullets that map stories to log sources and (optionally) MITRE ATT&CK techniques.\n"
        "4. `### Medium-term follow-ups` – 4–6 bullets for patching/backlog/hardening tasks.\n\n"
        "Constraints:\n"
        "- Keep bullets concise; avoid verbose paragraphs.\n"
        "- Group similar stories (e.g., multiple VPN CVEs = one bullet grouping).\n"
        "- State assumptions when details are incomplete.\n"
        "- Do not invent IOCs unless the context explicitly provides them.\n"
    )


# --------------------------------------------------------------------------- #
# OpenAI call + response parsing
# --------------------------------------------------------------------------- #

def extract_text_from_response(resp: Any) -> str:
    """Normalize Responses API outputs into plain text."""
    choice = resp.choices[0]

    content = getattr(choice.message, "content", "")
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "\n".join(parts).strip()

    if hasattr(choice, "response_text"):
        return getattr(choice, "response_text", "").strip()

    return ""


def call_openai(model: str, system_prompt: str, user_prompt: str) -> str:
    """Hit OpenAI's Responses API and return markdown text."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    print(f"[INFO] Calling OpenAI model={model}")

    try:
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        text = extract_text_from_response(resp)
        if not text:
            return (
                "### Daily briefing unavailable\n\n"
                "No content returned by the model. Please check API logs or try a smaller context window."
            )

        if text.strip().endswith(("-", "–")):
            text += (
                "\n\n---\n\n"
                "**[Note]** Output may have been truncated. Consider reducing context size or raising `DAILY_REPORT_MAX_OUTPUT_TOKENS`."
            )

        return text

    except APIError as e:
        if getattr(e, "code", "") == "insufficient_quota":
            print("[WARN] OpenAI quota exceeded")
            return (
                "### Daily briefing unavailable\n\n"
                "OpenAI API quota exceeded—daily briefing could not be generated."
            )
        raise


# --------------------------------------------------------------------------- #
# Output writer
# --------------------------------------------------------------------------- #

def save_output(
    markdown: str,
    curated: List[Dict[str, Any]],
    total_window_items: int,
    window_hours: int,
    meta: Dict[str, Any],
) -> Path:
    """Persist the briefing and highlights."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    date_str = now.date().isoformat()

    daily_path = OUTPUT_DIR / f"daily_report_{date_str}.json"
    latest_path = OUTPUT_DIR / "daily_report_latest.json"

    highlights = []
    for itm in curated[:10]:
        ts = itm.get("_published_ts") or itm.get("published_ts")
        published = (
            datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            if isinstance(ts, (int, float))
            else itm.get("published")
        )
        highlights.append(
            {
                "title": itm.get("title"),
                "link": itm.get("link"),
                "source": itm.get("source"),
                "published": published,
                "smart_groups": itm.get("smart_groups") or [],
                "curated": bool(itm.get("curated")),
            }
        )

    payload = {
        "generated_at": now.isoformat(),
        "analysis_date": date_str,
        "model": OPENAI_MODEL,
        "window_hours": window_hours,
        "source_file": str(NEWS_RECENT_PATH),
        "source_generated_at": meta.get("generated_at"),
        "source_days_back": meta.get("days_back"),
        "source_total_items": meta.get("total_items"),
        "total_items_in_window_all": total_window_items,
        "total_items_in_window_curated": len(curated),
        "daily_report_markdown": markdown,
        "highlights": highlights,
    }

    daily_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    latest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[INFO] Daily report saved → {daily_path}")
    print(f"[INFO] Updated alias → {latest_path}")
    return daily_path


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #

def main() -> None:
    news = load_news_recent(NEWS_RECENT_PATH)
    items = news["items"]

    window_items = filter_last_hours(items, WINDOW_HOURS)
    total_window_all = len(window_items)

    curated = filter_curated(window_items) or window_items
    if curated is window_items:
        print("[WARN] No curated items found; using all items in window.")

    subset = curated[:MAX_ITEMS_FOR_CONTEXT]
    print(f"[INFO] Using {len(subset)} items for model context.")

    context = build_context_snippet(subset)
    sys_prompt = build_system_prompt()
    user_prompt = build_user_prompt(context, WINDOW_HOURS, len(curated))

    markdown = call_openai(OPENAI_MODEL, sys_prompt, user_prompt)

    save_output(
        markdown=markdown,
        curated=curated,
        total_window_items=total_window_all,
        window_hours=WINDOW_HOURS,
        meta=news,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        sys.exit(1)
