#!/usr/bin/env python3
"""
daily_briefing.py - one LLM-written daily per vertical, from that day's archive.

Flow:
    1. Load every ``archive/<feed_type>/daily/<date>.json`` for the day
       (default: the previous complete UTC day), dedupe by link and title.
    2. Number the items and pack them into chunks that fit the lane's context
       (token budget, default 20k of the 32k lane).
    3. Map: each chunk -> a few candidate stories that cite item numbers.
    4. Reduce: candidates -> headline summary + top stories (re-chunked if the
       candidates themselves overflow the budget).
    5. Validate: keep only citations to real input items, turn them into links,
       drop any bullet left without a citation. Nothing reaches the page that
       is not traceable to an item link.
    6. Write ``archive/daily_report_<date>.json`` (replaced on re-run) and
       ``archive/daily_report_latest.json`` (only if this is the newest day).

If the LLM endpoint is unreachable the run prints why and exits 0 without
touching any file (``--strict`` makes it exit 2 instead).

Usage:
    python core/code/base/daily_briefing.py --vertical k5
    python core/code/base/daily_briefing.py --vertical 4u --date 2026-10-12
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))

from llm_client import LLMClient, LLMConfig, LLMError, LLMUnavailable  # noqa: E402
from path_utils import add_path_cli_arguments, load_path_config  # noqa: E402

DEFAULT_TOKEN_BUDGET = 20_000
SUMMARY_CHARS = 220
SOURCE_CHARS = 40
STORIES_PER_CHUNK = 8
TOP_STORIES = 8
HEADLINE_BULLETS = 3
HIGHLIGHT_LIMIT = 10
LINKS_PER_BULLET = 4  # shown on the page; the JSON keeps every cited link

AUDIENCES = {
    "k5": (
        "security practitioners (SOC analysts, incident responders, security leads)",
        "active exploitation, critical vulnerabilities, breaches, ransomware, "
        "supply-chain incidents and major vendor advisories",
    ),
    "4u": (
        "AI and machine-learning practitioners and technology readers",
        "major model and product releases, notable research, policy and regulation, "
        "large funding or business moves, and safety incidents",
    ),
}
DEFAULT_AUDIENCE = ("general readers of a news site", "the most significant developments")


# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #

def previous_utc_day(now: Optional[datetime] = None) -> date:
    now = now or datetime.now(timezone.utc)
    return (now - timedelta(days=1)).date()


def load_day_items(archive_dir: Path, day: date) -> List[Dict[str, Any]]:
    """All archived items for ``day`` across feed types, deduped, newest first."""
    items: List[Dict[str, Any]] = []
    for path in sorted(archive_dir.glob(f"*/daily/{day.isoformat()}.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[WARN] Skipping unreadable {path}: {exc}")
            continue
        rows = data.get("items", []) if isinstance(data, dict) else data
        for row in rows or []:
            if isinstance(row, dict) and row.get("link") and row.get("title"):
                row.setdefault("feed_type", path.parent.parent.name)
                items.append(row)
    return dedupe_items(items)


def _norm_title(title: str) -> str:
    return re.sub(r"\W+", " ", title.lower()).strip()


def dedupe_items(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_links, seen_titles, out = set(), set(), []
    for item in sorted(items, key=lambda i: i.get("published_ts") or 0, reverse=True):
        link = (item.get("link") or "").strip().rstrip("/")
        title = _norm_title(item.get("title") or "")
        if link in seen_links or (title and title in seen_titles):
            continue
        seen_links.add(link)
        if title:
            seen_titles.add(title)
        out.append(item)
    return out


def short_source(source: str) -> str:
    """'Engadget - Engadget is a web magazine…' -> 'Engadget'; a feed URL -> its domain."""
    if re.match(r"https?://", (source or "").strip()):
        host = urlparse(source.strip()).hostname or ""
        return host.removeprefix("www.")[:SOURCE_CHARS] or "source"
    name = re.split(r"\s+[-|–:]\s+", (source or "").strip(), maxsplit=1)[0]
    return name[:SOURCE_CHARS].strip() or "source"


def _clip(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def format_item_line(number: int, item: Dict[str, Any]) -> str:
    line = f"[{number}] {_clip(item.get('title') or '', 200)} ({short_source(item.get('source') or '')})"
    summary = _clip(item.get("summary") or "", SUMMARY_CHARS)
    if summary and _norm_title(summary) != _norm_title(item.get("title") or ""):
        line += f" — {summary}"
    return line


# --------------------------------------------------------------------------- #
# Chunking
# --------------------------------------------------------------------------- #

def estimate_tokens(text: str) -> int:
    """Conservative token estimate (~3 chars/token; real BPE is closer to 4)."""
    return math.ceil(len(text) / 3)


def chunk_lines(lines: Sequence[str], budget: int) -> List[List[str]]:
    """Greedy-pack lines into chunks whose estimated size stays within ``budget``.

    A single line larger than the budget is truncated to fit rather than dropped.
    """
    if budget <= 0:
        raise ValueError("token budget must be positive")
    chunks: List[List[str]] = []
    current: List[str] = []
    used = 0
    for line in lines:
        cost = estimate_tokens(line) + 1  # newline
        if cost > budget:
            line = line[: (budget - 1) * 3]
            cost = estimate_tokens(line) + 1
        if current and used + cost > budget:
            chunks.append(current)
            current, used = [], 0
        current.append(line)
        used += cost
    if current:
        chunks.append(current)
    return chunks


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #

RULES = (
    "Rules:\n"
    "- Use ONLY the numbered items given. Never add facts, names, numbers or links "
    "that are not in those items.\n"
    "- Every entry must cite the numbers of the items it is based on in \"ids\".\n"
    "- Do not write URLs. Write plain English, no markdown.\n"
    "- Answer with a single JSON object and nothing else."
)


def system_prompt(vertical: str) -> str:
    audience, priorities = AUDIENCES.get(vertical, DEFAULT_AUDIENCE)
    return (
        f"You are the editor of a daily news briefing for {audience}. "
        f"You prioritise {priorities}. You are precise and never speculate.\n\n{RULES}"
    )


def map_prompt(day: date, lines: Sequence[str], part: int, parts: int) -> str:
    return (
        f"Items published on {day.isoformat()} (part {part} of {parts}):\n\n"
        + "\n".join(lines)
        + "\n\nPick up to "
        f"{STORIES_PER_CHUNK} of the most important distinct stories in these items. "
        "Merge items that report the same story into one entry. Skip deals, "
        "promotions, how-to guides and minor items.\n"
        'Return {"stories": [{"title": "short headline", "summary": "one factual '
        'sentence", "ids": [item numbers]}]}'
    )


def reduce_prompt(day: date, candidates: Sequence[str], total_items: int) -> str:
    return (
        f"Candidate stories from {total_items} items published on {day.isoformat()}. "
        "Each candidate cites the item numbers it is based on.\n\n"
        + "\n".join(candidates)
        + "\n\nWrite the day's briefing:\n"
        f"- \"headline\": {HEADLINE_BULLETS} short sentences summarising the day, each "
        "with the ids it rests on.\n"
        f"- \"top_stories\": the {TOP_STORIES} most important stories, most important "
        "first, merging duplicates; keep the cited ids.\n"
        'Return {"headline": [{"text": "...", "ids": [..]}], "top_stories": '
        '[{"title": "...", "summary": "...", "ids": [..]}]}'
    )


def format_candidate(story: Dict[str, Any]) -> str:
    ids = ",".join(str(i) for i in story["ids"])
    return f"- [{ids}] {story['title']}: {story.get('summary', '')}"


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

_URL_RE = re.compile(r"https?://\S+|www\.\S+")


def _clean_text(value: Any, limit: int) -> str:
    text = _URL_RE.sub("", str(value or ""))
    text = re.sub(r"[\[\]`*_#<>]", "", text)  # no markdown/HTML injection
    return _clip(text, limit)


def _valid_ids(raw: Any, known: Dict[int, Dict[str, Any]]) -> List[int]:
    if not isinstance(raw, list):
        raw = [raw]
    out: List[int] = []
    for value in raw:
        try:
            number = int(str(value).strip().strip("[]"))
        except (TypeError, ValueError):
            continue
        if number in known and number not in out:
            out.append(number)
    return out


def validate_stories(raw: Any, known: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep stories with a title and at least one citation to a known item."""
    stories = raw.get("stories") if isinstance(raw, dict) else raw
    out = []
    for story in stories or []:
        if not isinstance(story, dict):
            continue
        ids = _valid_ids(story.get("ids"), known)
        title = _clean_text(story.get("title"), 160)
        if ids and title:
            out.append({"title": title, "summary": _clean_text(story.get("summary"), 400), "ids": ids})
    return out


def validate_briefing(raw: Any, known: Dict[int, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    raw = raw if isinstance(raw, dict) else {}
    headline = []
    for entry in raw.get("headline") or []:
        if isinstance(entry, dict):
            ids = _valid_ids(entry.get("ids"), known)
            text = _clean_text(entry.get("text"), 300)
            if ids and text:
                headline.append({"text": text, "ids": ids})
    stories = validate_stories({"stories": raw.get("top_stories")}, known)
    return {"headline": headline[:HEADLINE_BULLETS + 2], "top_stories": stories[:TOP_STORIES]}


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def _safe_link(url: str) -> Optional[str]:
    parsed = urlparse(url or "")
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return url.replace(")", "%29").replace(" ", "%20")
    return None


def _citations(ids: Sequence[int], known: Dict[int, Dict[str, Any]]) -> str:
    links = []
    for number in ids[:LINKS_PER_BULLET]:
        item = known[number]
        url = _safe_link(item.get("link") or "")
        if url:
            label = re.sub(r"[\[\]]", "", short_source(item.get("source") or ""))
            links.append(f"[{label}]({url})")
    return ", ".join(links)


def render_markdown(briefing: Dict[str, List[Dict[str, Any]]], known: Dict[int, Dict[str, Any]]) -> str:
    """Markdown in the subset the web page renders: ###, '- ', **bold**, [links]()."""
    lines = ["### Headline summary"]
    for entry in briefing["headline"]:
        lines.append(f"- {entry['text']} ({_citations(entry['ids'], known)})")
    lines += ["", "### Top stories"]
    for story in briefing["top_stories"]:
        summary = f" — {story['summary']}" if story["summary"] else ""
        lines.append(f"- **{story['title']}**{summary} ({_citations(story['ids'], known)})")
    return "\n".join(lines).strip()


def cited_items(briefing: Dict[str, List[Dict[str, Any]]], known: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    order: List[int] = []
    for section in ("top_stories", "headline"):
        for entry in briefing[section]:
            for number in entry["ids"]:
                if number not in order:
                    order.append(number)
    return [known[n] for n in order]


def to_highlight(item: Dict[str, Any]) -> Dict[str, Any]:
    ts = item.get("published_ts")
    published = (
        datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        if isinstance(ts, (int, float))
        else item.get("published")
    )
    return {
        "title": item.get("title"),
        "link": item.get("link"),
        "source": short_source(item.get("source") or ""),
        "published": published,
        "smart_groups": item.get("smart_groups") or [],
        "curated": bool(item.get("curated")),
    }


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #

class BriefingBuilder:
    def __init__(self, client: LLMClient, vertical: str, token_budget: int = DEFAULT_TOKEN_BUDGET):
        self.client = client
        self.vertical = vertical
        self.token_budget = token_budget
        self.calls = 0

    def _ask(self, prompt: str, max_tokens: int) -> Any:
        self.calls += 1
        messages = [
            {"role": "system", "content": system_prompt(self.vertical)},
            {"role": "user", "content": prompt},
        ]
        return self.client.chat_json(messages, max_tokens=max_tokens)

    def _map(self, day: date, chunks: List[List[str]], known: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        stories: List[Dict[str, Any]] = []
        for index, chunk in enumerate(chunks, start=1):
            started = time.monotonic()
            try:
                raw = self._ask(map_prompt(day, chunk, index, len(chunks)), max_tokens=2000)
            except LLMUnavailable:
                raise
            except LLMError as exc:
                print(f"[WARN] chunk {index}/{len(chunks)} unusable, skipped: {exc}")
                continue
            found = validate_stories(raw, known)
            print(
                f"[INFO] chunk {index}/{len(chunks)}: {len(chunk)} items -> "
                f"{len(found)} stories ({time.monotonic() - started:.1f}s)"
            )
            stories.extend(found)
        return stories

    def build(self, day: date, items: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[int, Dict[str, Any]], int]:
        known = {n: item for n, item in enumerate(items, start=1)}
        lines = [format_item_line(n, item) for n, item in known.items()]
        chunks = chunk_lines(lines, self.token_budget)
        print(f"[INFO] {len(items)} items in {len(chunks)} chunk(s), budget {self.token_budget} tokens")

        stories = self._map(day, chunks, known)
        # Collapse candidates until they fit one reduce prompt.
        candidates = [format_candidate(s) for s in stories]
        for _ in range(3):
            groups = chunk_lines(candidates, self.token_budget)
            if len(groups) <= 1:
                break
            print(f"[INFO] {len(candidates)} candidates overflow budget; merging in {len(groups)} groups")
            stories = self._map(day, groups, known)
            candidates = [format_candidate(s) for s in stories]
        candidates = chunk_lines(candidates, self.token_budget)[0] if candidates else []
        if not stories:
            raise LLMError("no valid stories came back from any chunk")

        raw = self._ask(reduce_prompt(day, candidates, len(items)), max_tokens=3000)
        briefing = validate_briefing(raw, known)
        if not briefing["top_stories"]:
            # The reducer cited nothing valid: fall back to the validated map output.
            briefing["top_stories"] = stories[:TOP_STORIES]
        return briefing, known, len(chunks)


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #

def write_outputs(archive_dir: Path, payload: Dict[str, Any]) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    day_str = payload["analysis_date"]
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    daily_path = archive_dir / f"daily_report_{day_str}.json"
    daily_path.write_text(text, encoding="utf-8")
    print(f"[INFO] Daily report saved → {daily_path}")

    latest_path = archive_dir / "daily_report_latest.json"
    latest_day = ""
    if latest_path.exists():
        try:
            latest_day = json.loads(latest_path.read_text(encoding="utf-8")).get("analysis_date") or ""
        except (OSError, json.JSONDecodeError):
            latest_day = ""
    if day_str >= latest_day:
        latest_path.write_text(text, encoding="utf-8")
        print(f"[INFO] Updated alias → {latest_path}")
    else:
        print(f"[INFO] Kept {latest_path} (it is for newer day {latest_day})")
    return daily_path


def run(
    *,
    archive_dir: Path,
    vertical: str,
    day: date,
    client: LLMClient,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    now: Optional[datetime] = None,
) -> Optional[Path]:
    """Build and write one daily. Returns the written path, or None if skipped.

    Raises LLMUnavailable if the endpoint is down (no file is written).
    """
    items = load_day_items(archive_dir, day)
    if not items:
        print(f"[INFO] No archived items for {vertical} on {day}; nothing to do.")
        return None
    client.check_available()

    started = time.monotonic()
    builder = BriefingBuilder(client, vertical, token_budget)
    briefing, known, chunk_count = builder.build(day, items)
    duration = round(time.monotonic() - started, 1)

    markdown = render_markdown(briefing, known)
    curated = sum(1 for item in items if item.get("curated"))
    payload = {
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(),
        "analysis_date": day.isoformat(),
        "vertical": vertical,
        "model": client.config.model,
        "llm_endpoint": urlparse(client.config.base_url).netloc,
        "window_hours": 24,
        "source_file": f"archive/*/daily/{day.isoformat()}.json",
        "total_items_in_window_all": len(items),
        "total_items_in_window_curated": curated,
        "chunks": chunk_count,
        "llm_calls": builder.calls,
        "duration_seconds": duration,
        "daily_report_markdown": markdown,
        "headline": [
            {"text": e["text"], "links": [known[n]["link"] for n in e["ids"]]} for e in briefing["headline"]
        ],
        "top_stories": [
            {"title": s["title"], "summary": s["summary"], "links": [known[n]["link"] for n in s["ids"]]}
            for s in briefing["top_stories"]
        ],
        "highlights": [to_highlight(item) for item in cited_items(briefing, known)[:HIGHLIGHT_LIMIT]],
    }
    print(
        f"[INFO] {vertical} {day}: {len(items)} items, {chunk_count} chunks, "
        f"{builder.calls} LLM calls, {duration}s, {len(markdown)} chars"
    )
    return write_outputs(archive_dir, payload)


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the LLM daily briefing for a vertical.")
    add_path_cli_arguments(parser)
    parser.add_argument("--date", help="UTC day YYYY-MM-DD (default: yesterday UTC)")
    parser.add_argument("--token-budget", type=int, default=DEFAULT_TOKEN_BUDGET,
                        help="Estimated input tokens per LLM call (default 20000 for a 32k lane)")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 2 instead of 0 when the LLM is unavailable")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)  # progress visible in logs during long runs
    config = load_path_config(
        base_dir=args.base_dir,
        data_dir=args.data_dir,
        vertical=args.vertical,
        archive_dir=args.archive_dir,
    )
    vertical = config.vertical or "k5"
    day = date.fromisoformat(args.date) if args.date else previous_utc_day()
    if day >= datetime.now(timezone.utc).date():
        print(f"[ERROR] {day} is not a complete UTC day yet")
        return 1

    client = LLMClient(LLMConfig.from_env())
    print(f"[INFO] Daily briefing for {vertical} {day} via {client.config.base_url} ({client.config.model})")
    try:
        run(archive_dir=config.archive_dir, vertical=vertical, day=day, client=client,
            token_budget=args.token_budget)
    except LLMUnavailable as exc:
        print(f"[SKIP] LLM unavailable, daily not built, no files changed: {exc}")
        return 2 if args.strict else 0
    except LLMError as exc:
        print(f"[SKIP] LLM gave no usable briefing, no files changed: {exc}")
        return 2 if args.strict else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
