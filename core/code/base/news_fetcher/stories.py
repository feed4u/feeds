"""Group different tellings of the same story.

Nine outlets covering "researchers used Claude to hack OpenAI" are one story
to a reader. This links items whose titles share enough distinctive words
within a time window, then picks one *primary* telling per story: the
earliest one from a non-aggregator source. Every member gets ``story_id`` and
``story_size``; the primary gets ``story_primary: true`` and a compact
``story_others`` list so the feed can say "also reported by …" without having
loaded the other members.

It is deliberately simple (token overlap, union-find). It is not trying to
be semantic; it is trying to stop the top of the feed repeating itself.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Set, Tuple

STOPWORDS = set(
    """
    the a an of to in on for and or with by from at as is are its it this that
    new says say said how why what will can be has have after over into vs
    about up out more than his her their our your not just one two first
    sources source report reports exclusive breaking show ask tell hn via
    """.split()
)

# Titles like "Sources: OpenAI raises $1B (Jane Doe/Bloomberg)" — the outlet
# suffix and the "Sources:" prefix are Techmeme's, not the story's.
_TRAILING_ATTRIBUTION = re.compile(r"\s*\([^()]*\)\s*$")
_LEADING_LABEL = re.compile(r"^(?:sources?|report|exclusive|breaking|update|show hn|ask hn|tell hn)\s*:\s*", re.IGNORECASE)
_NON_WORD = re.compile(r"[^a-z0-9 ]+")

MIN_TOKENS = 4
MAX_DF = 400  # ignore tokens that appear in more titles than this when finding candidates


def title_tokens(title: str) -> Set[str]:
    t = title.lower()
    t = _TRAILING_ATTRIBUTION.sub("", t)
    t = _LEADING_LABEL.sub("", t)
    t = t.split(" — ")[0].split(" | ")[0]
    t = _NON_WORD.sub(" ", t)
    return {w for w in t.split() if len(w) >= 3 and w not in STOPWORDS}


def _same_story(a: Set[str], b: Set[str], same_source: bool = False) -> bool:
    inter = len(a & b)
    if inter < 3:
        return False
    union = len(a | b)
    jaccard = inter / union
    if same_source:
        # One outlet rarely covers a story twice; near-identical titles from
        # the same feed are re-posts, template titles ("X now available on
        # AI Gateway") are not.
        return jaccard >= 0.75
    return (inter >= 4 and jaccard >= 0.4) or (inter >= 3 and jaccard >= 0.6)


def assign_stories(
    items: List[Dict[str, Any]],
    *,
    window_hours: int = 72,
    is_aggregator: Callable[[str], bool] = lambda source: False,
) -> Dict[str, int]:
    """Annotate ``items`` in place with story fields. Returns stats."""
    # Clear stale annotations (items are re-clustered on every run).
    for it in items:
        for k in ("story_id", "story_size", "story_primary", "story_others"):
            it.pop(k, None)

    toks: List[Set[str]] = [title_tokens(it.get("title", "")) for it in items]
    ts: List[int] = [int(it.get("published_ts") or 0) for it in items]
    window = window_hours * 3600

    index: Dict[str, List[int]] = defaultdict(list)
    for i, tk in enumerate(toks):
        if len(tk) >= MIN_TOKENS:
            for w in tk:
                index[w].append(i)

    parent = list(range(len(items)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[max(rx, ry)] = min(rx, ry)

    pairs = 0
    for i, tk in enumerate(toks):
        if len(tk) < MIN_TOKENS:
            continue
        candidates: Set[int] = set()
        for w in tk:
            posting = index[w]
            if len(posting) <= MAX_DF:
                candidates.update(posting)
        for j in candidates:
            if j <= i or find(i) == find(j):
                continue
            if ts[i] and ts[j] and abs(ts[i] - ts[j]) > window:
                continue
            if _same_story(tk, toks[j], items[i].get("source") == items[j].get("source")):
                union(i, j)
                pairs += 1

    groups: Dict[int, List[int]] = defaultdict(list)
    for i in range(len(items)):
        groups[find(i)].append(i)

    stories = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        stories += 1
        members.sort(key=lambda k: ts[k] or 2**62)  # earliest first
        primary = next((k for k in members if not is_aggregator(items[k].get("source", ""))), members[0])
        story_id = hashlib.sha1(items[primary]["link"].encode("utf-8")).hexdigest()[:12]
        for k in members:
            items[k]["story_id"] = story_id
            items[k]["story_size"] = len(members)
        items[primary]["story_primary"] = True
        items[primary]["story_others"] = [
            {
                "source": items[k].get("source", ""),
                "title": items[k].get("title", ""),
                "link": items[k].get("link", ""),
                "published_ts": ts[k] or None,
            }
            for k in members
            if k != primary
        ]

    return {"stories": stories, "linked_pairs": pairs, "items": len(items)}
