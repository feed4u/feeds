#!/usr/bin/env python3
"""
build_topics.py - group one day's stories into ranked topics.

Flow:
    1. Load every ``archive/<feed_type>/daily/<date>.json`` for the day
       (default: the previous complete UTC day), dedupe by link and title —
       the same input as the daily briefing.
    2. Rules first: ``news_fetcher.stories.assign_stories`` links different
       tellings of the same story (title token overlap). Those groups are the
       candidate clusters; feed type, category and smart group order them so
       related candidates land in the same LLM batch.
    3. LLM second (cheap on a 27B local model): each batch of candidates goes
       to the model once. It may keep, merge or split candidates and names
       every topic of two or more stories. Single stories are never sent back;
       they keep their own headline. When the day needed more than one batch,
       one more pass over the topic titles merges topics split across batches.
    4. Validate: a story number the model invents is dropped, a story it puts
       in two topics stays in the first, a story it forgets stays in its rule
       cluster. Every story ends up in exactly one topic.
    5. Rank in Python, not by the model: distinct sources, story count, then
       recency (see ``rank_topics``).
    6. Write ``archive/news/topics/<date>.json`` and ``topics_latest.json``
       (the latter only if this is the newest day).

If the LLM is unreachable or answers with unusable output, the affected
batches keep their rule clusters (``mode`` "rules" or "partial"); a good
LLM-built file for the day is never replaced by a rules-only one. Re-running
for a day whose input has not changed is a no-op (``--force`` rebuilds), and
a rebuild whose result is identical leaves the file untouched.

Per-vertical switch: ``TOPIC_VERTICALS`` below.

Usage:
    python core/code/base/build_topics.py --vertical k5
    python core/code/base/build_topics.py --vertical finnish --date 2026-10-12
    python core/code/base/build_topics.py --vertical 4u --rules-only
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))

from daily_briefing import (  # noqa: E402
    _clean_text,
    _clip,
    _norm_title,
    estimate_tokens,
    load_day_items,
    previous_utc_day,
    short_source,
)
from llm_client import LLMClient, LLMConfig, LLMError, LLMUnavailable  # noqa: E402
from path_utils import add_path_cli_arguments, load_path_config  # noqa: E402


def _load_stories_module():
    # Load stories.py by path: importing the news_fetcher package would pull in
    # feedparser (via its processor), which the host-side job does not need.
    path = Path(__file__).parent / "news_fetcher" / "stories.py"
    spec = importlib.util.spec_from_file_location("news_fetcher_stories", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


assign_stories = _load_stories_module().assign_stories

SCHEMA_VERSION = 1

# Which verticals get LLM topics. Set one to False to switch it off.
TOPIC_VERTICALS: Dict[str, bool] = {
    "4u": True,
    "k5": True,
    "finnish": True,
    "economics": True,
    "storage": True,
}

DEFAULT_TOKEN_BUDGET = 12_000  # input tokens per batch; replies stay well inside a 32k lane
ITEMS_PER_BATCH = 120  # beyond this a 27B model starts to lose track of story numbers
TOPICS_PER_MERGE_BATCH = 300
PROMPT_TITLE_CHARS = 160
PROMPT_SUMMARY_CHARS = 100
STORY_SUMMARY_CHARS = 300
TOPIC_TITLE_CHARS = 120
TOPIC_SUMMARY_CHARS = 400
SEND_ALL_BATCHES = 3  # days that fit in this many batches send every story to the LLM
STEM_CHARS = 5
STEM_MIN_COMMON = 5  # a stem in more candidates than this (or the share below) says nothing
STEM_COMMON_SHARE = 0.03
CHUNK_MAX_TOKENS = 4000
MERGE_MAX_TOKENS = 2000

MODES = ("llm", "partial", "rules")
VOLATILE_KEYS = ("generated_at",)
VOLATILE_STATS = ("duration_seconds",)


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

def topics_dir(archive_dir: Path) -> Path:
    return archive_dir / "news" / "topics"


def topics_path(archive_dir: Path, day: date) -> Path:
    return topics_dir(archive_dir) / f"{day.isoformat()}.json"


def load_day_topics(archive_dir: Path, day: date) -> Optional[Dict[str, Any]]:
    """The day's topics file if it exists and is valid, else None."""
    path = topics_path(archive_dir, day)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[WARN] Ignoring unreadable {path}: {exc}")
        return None
    errors = validate_topics_payload(payload)
    if errors:
        print(f"[WARN] Ignoring invalid {path}: {errors[0]}")
        return None
    return payload


# --------------------------------------------------------------------------- #
# Rules: candidate clusters
# --------------------------------------------------------------------------- #

def rule_candidates(items: List[Dict[str, Any]]) -> List[List[int]]:
    """Group item indexes with the feed's story rules, in batch order.

    Related candidates sit next to each other (same feed type, category and
    first smart group) so they tend to share an LLM batch.
    """
    copies = [dict(item) for item in items]
    assign_stories(copies, window_hours=48)
    groups: Dict[str, List[int]] = defaultdict(list)
    for index, item in enumerate(copies):
        groups[item.get("story_id") or f"single-{index}"].append(index)

    def order_key(members: List[int]) -> Tuple[Any, ...]:
        first = items[members[0]]
        hint = (first.get("smart_groups") or ["~"])[0]
        return (
            first.get("feed_type") or "",
            first.get("type") or "",
            hint,
            -len(members),
            min(int(items[k].get("published_ts") or 0) for k in members),
            first.get("link") or "",
        )

    clusters = [sorted(m, key=lambda k: (int(items[k].get("published_ts") or 0), items[k]["link"]))
                for m in groups.values()]
    return sorted(clusters, key=order_key)


_WORD = re.compile(r"\w+", re.UNICODE)


def title_stems(title: str) -> Set[str]:
    """Crude stems (first 5 letters of words of 4+ letters) so inflected forms
    match: "Microsoftin"/"Microsoft", "hospitals"/"hospital"."""
    return {w[:STEM_CHARS] for w in _WORD.findall((title or "").lower()) if len(w) >= 4 and not w.isdigit()}


def related_groups(candidates: List[List[int]], items: List[Dict[str, Any]]) -> List[List[List[int]]]:
    """Join candidates whose titles share at least two uncommon stems.

    Looser than the story rules: it only decides which candidates the LLM gets
    to compare. A single story related to nothing is never sent to the LLM; it
    stays its own topic under its own headline. Groups keep candidate order.
    """
    stems = [set().union(*(title_stems(items[k].get("title") or "") for k in members)) for members in candidates]
    df: Dict[str, int] = defaultdict(int)
    for group in stems:
        for stem in group:
            df[stem] += 1
    common = max(STEM_MIN_COMMON, int(len(candidates) * STEM_COMMON_SHARE))
    postings: Dict[str, List[int]] = defaultdict(list)
    for c, group in enumerate(stems):
        stems[c] = {s for s in group if df[s] <= common}
        for stem in stems[c]:
            postings[stem].append(c)

    parent = list(range(len(candidates)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for c, group in enumerate(stems):
        shared: Dict[int, int] = defaultdict(int)
        for stem in group:
            for other in postings[stem]:
                if other > c:
                    shared[other] += 1
        for other, count in shared.items():
            if count >= 2:
                a, b = find(c), find(other)
                if a != b:
                    parent[max(a, b)] = min(a, b)

    groups: Dict[int, List[List[int]]] = defaultdict(list)
    for c, members in enumerate(candidates):
        groups[find(c)].append(members)
    return [groups[root] for root in sorted(groups)]


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = (
    "You group a news site's stories of one day into topics. A topic is one news "
    "event or one specific development: different outlets reporting the same thing, "
    "or direct follow-ups to it. Never make broad themes such as \"AI news\", "
    "\"security updates\" or \"local news\". You are precise and never speculate.\n\n"
    "Rules:\n"
    "- Use ONLY the numbered stories given. Never add facts, names or numbers that are "
    "not in them.\n"
    "- Write titles and summaries in the language of the stories. No markdown, no URLs.\n"
    "- Answer with a single JSON object and nothing else."
)


def format_story_line(number: int, item: Dict[str, Any]) -> str:
    line = f"[{number}] {_clip(item.get('title') or '', PROMPT_TITLE_CHARS)} ({short_source(item.get('source') or '')})"
    summary = _clip(item.get("summary") or "", PROMPT_SUMMARY_CHARS)
    if summary and _norm_title(summary) != _norm_title(item.get("title") or ""):
        line += f" — {summary}"
    return line


def format_candidate_block(members: Sequence[int], items: List[Dict[str, Any]]) -> List[str]:
    """One line per story; a multi-story candidate is indented under a marker."""
    if len(members) == 1:
        return [format_story_line(members[0] + 1, items[members[0]])]
    return ["*"] + ["  " + format_story_line(k + 1, items[k]) for k in members]


def batch_prompt(day: date, lines: Sequence[str], part: int, parts: int) -> str:
    return (
        f"Stories published on {day.isoformat()} (batch {part} of {parts}). "
        "A line \"*\" starts a pre-grouped block: rules think its indented stories "
        "report the same event.\n\n"
        + "\n".join(lines)
        + "\n\nGroup these stories into topics:\n"
        "- Keep a pre-grouped block together if its stories are the same event; split "
        "it if they are not.\n"
        "- Merge stories and blocks that report the same event or development.\n"
        "- Stories that merely share a subject are separate topics: two research papers "
        "on the same problem, two vulnerabilities, two deals or two opinion pieces stay "
        "apart unless they are the same paper, flaw, deal or event.\n"
        "- Each story number may appear in at most one topic.\n"
        "- List every topic that has 2 or more stories. Leave single stories out.\n"
        "- \"title\": a short neutral headline (at most 12 words). \"summary\": 1-2 "
        "factual sentences based only on the given stories.\n"
        'Return {"topics": [{"title": "...", "summary": "...", "ids": [story numbers]}]}'
    )


def merge_prompt(day: date, lines: Sequence[str]) -> str:
    return (
        f"Topics found in separate batches of the stories published on {day.isoformat()}. "
        "Some may be the same event split across batches.\n\n"
        + "\n".join(lines)
        + "\n\nList only groups of topics that report the same event or development "
        "and should be one topic. Leave every other topic out. Give each merged topic "
        "a short neutral headline and a 1-2 sentence factual summary.\n"
        'Return {"merges": [{"ids": ["T1", "T7"], "title": "...", "summary": "..."}]} '
        '(an empty list if nothing should merge).'
    )


# --------------------------------------------------------------------------- #
# Batching
# --------------------------------------------------------------------------- #

def pack_batches(
    candidates: List[List[int]], items: List[Dict[str, Any]], budget: int, max_items: int
) -> List[List[List[int]]]:
    """Greedy-pack whole candidates into batches within ``budget`` tokens and
    ``max_items`` stories. A candidate is never split across batches (one that
    alone exceeds the limits gets a batch of its own)."""
    batches: List[List[List[int]]] = []
    current: List[List[int]] = []
    used_tokens = used_items = 0
    for members in candidates:
        cost = sum(estimate_tokens(line) + 1 for line in format_candidate_block(members, items))
        if current and (used_tokens + cost > budget or used_items + len(members) > max_items):
            batches.append(current)
            current, used_tokens, used_items = [], 0, 0
        current.append(members)
        used_tokens += cost
        used_items += len(members)
    if current:
        batches.append(current)
    return batches


# --------------------------------------------------------------------------- #
# Validation of model replies
# --------------------------------------------------------------------------- #

def _numbers(raw: Any) -> List[int]:
    if not isinstance(raw, list):
        raw = [raw]
    out: List[int] = []
    for value in raw:
        try:
            number = int(str(value).strip().strip("[]#").lstrip("Tt"))
        except (TypeError, ValueError):
            continue
        if number not in out:
            out.append(number)
    return out


def apply_batch_reply(
    raw: Any, batch: List[List[int]], assigned: Set[int]
) -> List[Dict[str, Any]]:
    """Turn one batch reply into topics; every story of the batch lands in one.

    ``assigned`` (item indexes already placed) is updated in place.
    """
    allowed = {k for members in batch for k in members}
    topics: List[Dict[str, Any]] = []
    entries = raw.get("topics") if isinstance(raw, dict) else raw
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        members = [n - 1 for n in _numbers(entry.get("ids"))]
        members = [k for k in members if k in allowed and k not in assigned]
        title = _clean_text(entry.get("title"), TOPIC_TITLE_CHARS)
        if not members or not title:
            continue
        assigned.update(members)
        topics.append({
            "members": members,
            "title": title,
            "summary": _clean_text(entry.get("summary"), TOPIC_SUMMARY_CHARS),
            "origin": "llm",
        })
    topics.extend(rule_topics(batch, assigned))
    return topics


def rule_topics(batch: List[List[int]], assigned: Set[int]) -> List[Dict[str, Any]]:
    """Whatever the model did not place stays in its rule cluster."""
    topics = []
    for members in batch:
        rest = [k for k in members if k not in assigned]
        if rest:
            assigned.update(rest)
            topics.append({"members": rest, "title": None, "summary": None, "origin": "rules"})
    return topics


def apply_merge_reply(raw: Any, topics: List[Dict[str, Any]], labels: Dict[int, int]) -> int:
    """Merge topics the model says are one. ``labels`` maps T-number -> index
    into ``topics``. Merged-away topics are emptied. Returns merges applied."""
    merges = 0
    used: Set[int] = set()
    entries = raw.get("merges") if isinstance(raw, dict) else raw
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        targets = [labels[n] for n in _numbers(entry.get("ids")) if n in labels]
        targets = [t for t in dict.fromkeys(targets) if t not in used and topics[t]["members"]]
        title = _clean_text(entry.get("title"), TOPIC_TITLE_CHARS)
        if len(targets) < 2 or not title:
            continue
        used.update(targets)
        keep = topics[targets[0]]
        for other in targets[1:]:
            keep["members"].extend(topics[other]["members"])
            topics[other]["members"] = []
        keep.update(title=title, summary=_clean_text(entry.get("summary"), TOPIC_SUMMARY_CHARS), origin="llm")
        merges += 1
    return merges


# --------------------------------------------------------------------------- #
# Ranking and output records
# --------------------------------------------------------------------------- #

def _first_sentences(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return _clip(" ".join(sentences[:2]), limit)


def story_record(item: Dict[str, Any]) -> Dict[str, Any]:
    ts = item.get("published_ts")
    return {
        "title": item.get("title") or "",
        "summary": _clip(item.get("summary") or "", STORY_SUMMARY_CHARS),
        "link": item.get("link") or "",
        "source": item.get("source") or "",
        "feed_type": item.get("feed_type") or "news",
        "type": item.get("type") or "",
        "type_label": item.get("type_label") or "",
        "published": item.get("published")
        or (datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if isinstance(ts, (int, float)) else None),
        "published_ts": int(ts) if isinstance(ts, (int, float)) else None,
        "smart_groups": list(item.get("smart_groups") or []),
        "curated": bool(item.get("curated")),
    }


def topic_record(topic: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
    members = sorted(set(topic["members"]),
                     key=lambda k: (int(items[k].get("published_ts") or 0), items[k]["link"]))
    stories = [story_record(items[k]) for k in members]
    lead = stories[0]
    sources = sorted({short_source(s["source"]) for s in stories})
    stamps = [s["published_ts"] for s in stories if s["published_ts"]]
    links = "\n".join(sorted(s["link"] for s in stories))
    return {
        "id": hashlib.sha1(links.encode("utf-8")).hexdigest()[:12],
        "rank": 0,
        "title": topic.get("title") or _clean_text(lead["title"], TOPIC_TITLE_CHARS) or lead["title"][:TOPIC_TITLE_CHARS],
        "summary": topic.get("summary") or _first_sentences(lead["summary"], TOPIC_SUMMARY_CHARS),
        "origin": topic["origin"] if topic.get("title") else "rules",
        "size": len(stories),
        "source_count": len(sources),
        "sources": sources,
        "first_ts": min(stamps) if stamps else None,
        "latest_ts": max(stamps) if stamps else None,
        "score": importance(len(stories), len(sources)),
        "stories": stories,
    }


def importance(size: int, source_count: int) -> int:
    """Independent outlets weigh more than one outlet posting many times."""
    return 2 * source_count + size


def rank_topics(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Most important first: score (sources, stories), then most recent, then id."""
    ranked = sorted(records, key=lambda t: (-t["score"], -(t["latest_ts"] or 0), t["id"]))
    for rank, record in enumerate(ranked, start=1):
        record["rank"] = rank
    return ranked


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #

class TopicBuilder:
    def __init__(
        self,
        client: Optional[LLMClient],
        token_budget: int = DEFAULT_TOKEN_BUDGET,
        items_per_batch: int = ITEMS_PER_BATCH,
    ):
        self.client = client
        self.token_budget = token_budget
        self.items_per_batch = items_per_batch
        self.calls = 0
        self.batches = 0
        self.batches_failed = 0
        self.merges = 0
        self.sent = 0
        self.llm_down = client is None

    def _ask(self, prompt: str, max_tokens: int) -> Any:
        assert self.client is not None
        self.calls += 1
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
        return self.client.chat_json(messages, max_tokens=max_tokens, temperature=0.0)

    def build(self, day: date, items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[List[int]]]:
        candidates = rule_candidates(items)
        groups = related_groups(candidates, items)
        to_send = [members for group in groups for members in group]
        alone: List[List[int]] = []
        batches = pack_batches(to_send, items, self.token_budget, self.items_per_batch)
        if len(batches) > SEND_ALL_BATCHES:
            # A big day: only stories with a plausible partner go to the LLM.
            to_send = [m for g in groups if len(g) > 1 or len(g[0]) > 1 for m in g]
            alone = [g[0] for g in groups if len(g) == 1 and len(g[0]) == 1]
            batches = pack_batches(to_send, items, self.token_budget, self.items_per_batch)
        self.batches = len(batches)
        self.sent = sum(len(m) for m in to_send)
        print(f"[INFO] {len(items)} stories, {len(candidates)} rule candidates; "
              f"{self.sent} related stories in {len(batches)} batch(es), "
              f"{len(alone)} unrelated stories stay single")

        assigned: Set[int] = set()
        topics: List[Dict[str, Any]] = rule_topics(alone, assigned)
        for index, batch in enumerate(batches, start=1):
            if self.llm_down:
                topics.extend(rule_topics(batch, assigned))
                continue
            lines = [line for members in batch for line in format_candidate_block(members, items)]
            started = time.monotonic()
            try:
                raw = self._ask(batch_prompt(day, lines, index, len(batches)), CHUNK_MAX_TOKENS)
            except LLMUnavailable as exc:
                print(f"[WARN] LLM became unavailable at batch {index}; rules for the rest: {exc}")
                self.llm_down = True
                self.batches_failed += 1
                topics.extend(rule_topics(batch, assigned))
                continue
            except LLMError as exc:
                print(f"[WARN] batch {index}/{len(batches)} unusable, rules kept: {exc}")
                self.batches_failed += 1
                topics.extend(rule_topics(batch, assigned))
                continue
            found = apply_batch_reply(raw, batch, assigned)
            print(
                f"[INFO] batch {index}/{len(batches)}: {sum(len(m) for m in batch)} stories -> "
                f"{sum(1 for t in found if t['origin'] == 'llm')} named topics "
                f"({time.monotonic() - started:.1f}s)"
            )
            topics.extend(found)

        if len(batches) > 1 and not self.llm_down and self.batches_failed < len(batches):
            self._merge_across_batches(day, topics[len(alone):], items)
        return [t for t in topics if t["members"]], candidates

    def _merge_across_batches(self, day: date, topics: List[Dict[str, Any]], items: List[Dict[str, Any]]) -> None:
        def label_title(topic: Dict[str, Any]) -> str:
            return topic.get("title") or items[topic["members"][0]].get("title") or ""

        order = sorted(range(len(topics)), key=lambda t: (_norm_title(label_title(topics[t])), t))
        lines = [f"T{t + 1}: {_clip(label_title(topics[t]), PROMPT_TITLE_CHARS)} ({len(topics[t]['members'])} stories)"
                 for t in order]
        groups: List[List[str]] = []
        for start in range(0, len(lines), TOPICS_PER_MERGE_BATCH):
            part = lines[start:start + TOPICS_PER_MERGE_BATCH]
            current: List[str] = []
            used = 0
            for line in part:
                cost = estimate_tokens(line) + 1
                if current and used + cost > self.token_budget:
                    groups.append(current)
                    current, used = [], 0
                current.append(line)
                used += cost
            if current:
                groups.append(current)
        labels = {t + 1: t for t in range(len(topics))}
        for group in groups:
            try:
                raw = self._ask(merge_prompt(day, group), MERGE_MAX_TOKENS)
            except LLMUnavailable as exc:
                print(f"[WARN] LLM unavailable during merge pass; stopping it: {exc}")
                self.llm_down = True
                return
            except LLMError as exc:
                print(f"[WARN] merge pass reply unusable, skipped: {exc}")
                continue
            self.merges += apply_merge_reply(raw, topics, labels)
        print(f"[INFO] merge pass over {len(lines)} topics in {len(groups)} call(s): {self.merges} merges")


def input_fingerprint(items: Iterable[Dict[str, Any]]) -> str:
    links = "\n".join(sorted(item["link"] for item in items))
    return hashlib.sha1(links.encode("utf-8")).hexdigest()[:16]


def grouping_stats(records: List[Dict[str, Any]], candidates: List[List[int]], items: List[Dict[str, Any]]) -> Dict[str, int]:
    """How the final topics differ from the rule candidates."""
    topic_of = {story["link"]: record["id"] for record in records for story in record["stories"]}
    candidate_of = {items[k]["link"]: c for c, members in enumerate(candidates) for k in members}
    merged = sum(1 for r in records if len({candidate_of[s["link"]] for s in r["stories"]}) > 1)
    split = sum(1 for members in candidates
                if len(members) > 1 and len({topic_of[items[k]["link"]] for k in members}) > 1)
    return {
        "rule_candidates": len(candidates),
        "rule_multi_story_candidates": sum(1 for m in candidates if len(m) > 1),
        "topics_merging_candidates": merged,
        "candidates_split": split,
    }


def build_payload(
    *,
    vertical: str,
    day: date,
    items: List[Dict[str, Any]],
    builder: TopicBuilder,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    started = time.monotonic()
    topics, candidates = builder.build(day, items)
    records = rank_topics([topic_record(t, items) for t in topics])
    duration = round(time.monotonic() - started, 1)

    if builder.client is None or (builder.batches and builder.batches_failed == builder.batches):
        mode = "rules"
    elif builder.batches_failed or builder.llm_down:
        mode = "partial"
    else:
        mode = "llm"
    usage = builder.client.usage if builder.client is not None else {}
    stats = {
        "items": len(items),
        "topics": len(records),
        "multi_story_topics": sum(1 for r in records if r["size"] > 1),
        "singletons": sum(1 for r in records if r["size"] == 1),
        "largest_topic": max((r["size"] for r in records), default=0),
        "llm_named_topics": sum(1 for r in records if r["origin"] == "llm"),
        **grouping_stats(records, candidates, items),
        "llm_merges_across_batches": builder.merges,
        "stories_sent_to_llm": builder.sent,
        "batches": builder.batches,
        "batches_failed": builder.batches_failed,
        "llm_calls": builder.calls,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "duration_seconds": duration,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "vertical": vertical,
        "date": day.isoformat(),
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(),
        "mode": mode,
        "model": builder.client.config.model if builder.client is not None else None,
        "llm_endpoint": urlparse(builder.client.config.base_url).netloc if builder.client is not None else None,
        "input_fingerprint": input_fingerprint(items),
        "stats": stats,
        "topics": records,
    }


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #

_TOP_LEVEL = {
    "schema_version": int, "vertical": str, "date": str, "generated_at": str, "mode": str,
    "input_fingerprint": str, "stats": dict, "topics": list,
}
_TOPIC_FIELDS = {
    "id": str, "rank": int, "title": str, "summary": str, "origin": str, "size": int,
    "source_count": int, "sources": list, "score": int, "stories": list,
}
_STORY_FIELDS = {
    "title": str, "summary": str, "link": str, "source": str, "feed_type": str,
    "smart_groups": list, "curated": bool,
}
_STAT_FIELDS = ("items", "topics", "multi_story_topics", "singletons", "largest_topic", "llm_calls")


def validate_topics_payload(payload: Any) -> List[str]:
    """Return every way ``payload`` breaks the topics schema (empty = valid)."""
    errors: List[str] = []
    if not isinstance(payload, dict):
        return ["payload is not an object"]
    for key, kind in _TOP_LEVEL.items():
        if not isinstance(payload.get(key), kind) or isinstance(payload.get(key), bool) and kind is int:
            errors.append(f"{key}: expected {kind.__name__}")
    if errors:
        return errors
    if payload["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version: expected {SCHEMA_VERSION}")
    if payload["mode"] not in MODES:
        errors.append(f"mode: {payload['mode']!r} not in {MODES}")
    try:
        date.fromisoformat(payload["date"])
    except ValueError:
        errors.append("date: not YYYY-MM-DD")
    for key in ("model", "llm_endpoint"):
        if payload.get(key) is not None and not isinstance(payload.get(key), str):
            errors.append(f"{key}: expected string or null")

    seen_links: Set[str] = set()
    seen_ids: Set[str] = set()
    for position, topic in enumerate(payload["topics"], start=1):
        where = f"topics[{position - 1}]"
        if not isinstance(topic, dict):
            errors.append(f"{where}: not an object")
            continue
        bad = [k for k, kind in _TOPIC_FIELDS.items() if not isinstance(topic.get(k), kind)]
        if bad:
            errors.append(f"{where}: bad or missing {', '.join(bad)}")
            continue
        if topic["rank"] != position:
            errors.append(f"{where}: rank {topic['rank']} != position {position}")
        if topic["id"] in seen_ids:
            errors.append(f"{where}: duplicate id {topic['id']}")
        seen_ids.add(topic["id"])
        if not topic["title"].strip():
            errors.append(f"{where}: empty title")
        if topic["origin"] not in ("llm", "rules"):
            errors.append(f"{where}: origin {topic['origin']!r}")
        if not topic["stories"]:
            errors.append(f"{where}: no stories")
        if topic["size"] != len(topic["stories"]):
            errors.append(f"{where}: size {topic['size']} != {len(topic['stories'])} stories")
        if topic["source_count"] != len(topic["sources"]):
            errors.append(f"{where}: source_count != len(sources)")
        for story in topic["stories"]:
            if not isinstance(story, dict) or any(not isinstance(story.get(k), kind) for k, kind in _STORY_FIELDS.items()):
                errors.append(f"{where}: malformed story")
                continue
            if story["link"] in seen_links:
                errors.append(f"{where}: story {story['link']} is in more than one topic")
            seen_links.add(story["link"])

    stats = payload["stats"]
    for key in _STAT_FIELDS:
        if not isinstance(stats.get(key), int):
            errors.append(f"stats.{key}: expected int")
    if not errors:
        topics = payload["topics"]
        expected = {
            "items": len(seen_links),
            "topics": len(topics),
            "multi_story_topics": sum(1 for t in topics if t["size"] > 1),
            "singletons": sum(1 for t in topics if t["size"] == 1),
            "largest_topic": max((t["size"] for t in topics), default=0),
        }
        for key, value in expected.items():
            if stats[key] != value:
                errors.append(f"stats.{key}: {stats[key]} != {value}")
    return errors


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #

def _stable_view(payload: Dict[str, Any]) -> Dict[str, Any]:
    view = {k: v for k, v in payload.items() if k not in VOLATILE_KEYS}
    view["stats"] = {k: v for k, v in payload.get("stats", {}).items() if k not in VOLATILE_STATS}
    return view


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_outputs(archive_dir: Path, payload: Dict[str, Any]) -> Path:
    errors = validate_topics_payload(payload)
    if errors:
        raise ValueError(f"refusing to write invalid topics: {errors[:3]}")
    out_dir = topics_dir(archive_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    day_path = out_dir / f"{payload['date']}.json"
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    existing = _read_json(day_path)
    if existing is not None and _stable_view(existing) == _stable_view(payload):
        print(f"[INFO] {day_path} unchanged")
        text = day_path.read_text(encoding="utf-8")
    else:
        day_path.write_text(text, encoding="utf-8")
        print(f"[INFO] Topics saved → {day_path}")

    latest_path = out_dir / "topics_latest.json"
    latest = _read_json(latest_path) or {}
    latest_day = latest.get("date") or ""
    if payload["date"] >= latest_day:
        if not latest_path.exists() or latest_path.read_text(encoding="utf-8") != text:
            latest_path.write_text(text, encoding="utf-8")
            print(f"[INFO] Updated alias → {latest_path}")
    else:
        print(f"[INFO] Kept {latest_path} (it is for newer day {latest_day})")
    return day_path


def run(
    *,
    archive_dir: Path,
    vertical: str,
    day: date,
    client: Optional[LLMClient],
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    items_per_batch: int = ITEMS_PER_BATCH,
    force: bool = False,
    now: Optional[datetime] = None,
) -> Optional[Path]:
    """Build and write one day's topics. Returns the path, or None if skipped.

    ``client=None`` builds rule-only topics.
    """
    items = load_day_items(archive_dir, day)
    if not items:
        print(f"[INFO] No archived items for {vertical} on {day}; nothing to do.")
        return None

    path = topics_path(archive_dir, day)
    existing = load_day_topics(archive_dir, day)
    fingerprint = input_fingerprint(items)
    if existing and not force and existing["input_fingerprint"] == fingerprint and (
        existing["mode"] == "llm" or client is None
    ):
        print(f"[INFO] {path} is current for these {len(items)} stories ({existing['mode']}); "
              "nothing to do (--force rebuilds)")
        return path

    if client is not None:
        try:
            client.check_available()
        except LLMUnavailable as exc:
            if existing and existing["mode"] in ("llm", "partial"):
                print(f"[SKIP] LLM unavailable; keeping the existing {existing['mode']} topics: {exc}")
                return path
            print(f"[WARN] LLM unavailable, writing rule-based topics: {exc}")
            client = None

    builder = TopicBuilder(client, token_budget, items_per_batch)
    payload = build_payload(vertical=vertical, day=day, items=items, builder=builder, now=now)
    if existing and existing["mode"] in ("llm", "partial") and payload["mode"] == "rules" and client is not None:
        print("[SKIP] every LLM batch failed; keeping the existing topics")
        return path
    stats = payload["stats"]
    print(
        f"[INFO] {vertical} {day}: {stats['items']} stories -> {stats['topics']} topics "
        f"({stats['multi_story_topics']} multi-story, {stats['singletons']} singletons, "
        f"largest {stats['largest_topic']}), mode {payload['mode']}, {stats['llm_calls']} LLM calls, "
        f"{stats['prompt_tokens']}+{stats['completion_tokens']} tokens, {stats['duration_seconds']}s"
    )
    return write_outputs(archive_dir, payload)


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Group one day's stories into ranked topics.")
    add_path_cli_arguments(parser)
    parser.add_argument("--date", help="UTC day YYYY-MM-DD (default: yesterday UTC)")
    parser.add_argument("--token-budget", type=int, default=DEFAULT_TOKEN_BUDGET,
                        help=f"Estimated input tokens per LLM batch (default {DEFAULT_TOKEN_BUDGET})")
    parser.add_argument("--items-per-batch", type=int, default=ITEMS_PER_BATCH,
                        help=f"Stories per LLM batch (default {ITEMS_PER_BATCH})")
    parser.add_argument("--rules-only", action="store_true", help="Do not call the LLM")
    parser.add_argument("--force", action="store_true", help="Rebuild even if the day's topics are current")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    config = load_path_config(
        base_dir=args.base_dir,
        data_dir=args.data_dir,
        vertical=args.vertical,
        archive_dir=args.archive_dir,
    )
    vertical = config.vertical or "k5"
    if not TOPIC_VERTICALS.get(vertical, False):
        print(f"[SKIP] Topics are switched off for {vertical} (TOPIC_VERTICALS in {Path(__file__).name})")
        return 0
    day = date.fromisoformat(args.date) if args.date else previous_utc_day()
    if day >= datetime.now(timezone.utc).date():
        print(f"[ERROR] {day} is not a complete UTC day yet")
        return 1

    client: Optional[LLMClient] = None
    if not args.rules_only:
        llm_config = LLMConfig.from_env()
        # Shared lanes: one retry at most, never a hammering loop.
        llm_config.retries = min(llm_config.retries, 1)
        client = LLMClient(llm_config)
        print(f"[INFO] Topics for {vertical} {day} via {llm_config.base_url} ({llm_config.model})")
    run(archive_dir=config.archive_dir, vertical=vertical, day=day, client=client,
        token_budget=args.token_budget, items_per_batch=args.items_per_batch, force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
