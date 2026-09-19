"""Item-level quality rules: relevance gating, boilerplate, dates.

Everything here is driven by a per-vertical *policy* module
(``code/<vertical>/policy.py``) so the base pipeline stays generic. A vertical
that has no policy module gets ``DEFAULT_POLICY`` (no gating, no curated
keywords beyond the base list).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path
from typing import Iterable, List, Optional, Pattern, Set

from .config import CURATED_KEYWORDS as BASE_CURATED_KEYWORDS


@dataclass
class Policy:
    """What a vertical considers relevant, curated and aggregated."""

    # Items from sources whose OPML category slug is in this set must mention
    # at least one topic term, unless the feed title itself signals the topic.
    gated_source_types: Set[str] = field(default_factory=set)
    topic_terms: Optional[Pattern] = None
    exempt_source_pattern: Optional[Pattern] = None
    # arXiv "Announce Type" values to drop (re-announced revisions, cross-lists).
    drop_arxiv_announce_types: Set[str] = field(
        default_factory=lambda: {"replace", "cross", "replace-cross"}
    )
    curated_keywords: List[str] = field(default_factory=lambda: list(BASE_CURATED_KEYWORDS))
    # Feed titles matching this are aggregators (Techmeme, HN, newsletters):
    # never chosen as a story's primary telling.
    aggregator_pattern: Optional[Pattern] = None
    max_smart_groups: int = 3
    # "always": title then summary; "fallback": title decides, summary only
    # when the title matched nothing (see classifiers module docstring).
    summary_mode: str = "always"
    story_window_hours: int = 72


DEFAULT_POLICY = Policy()


def load_policy(vertical: Optional[str], code_dir: Optional[Path] = None) -> Policy:
    """Load ``<vertical>/policy.py`` if present, else the default policy."""
    if not vertical:
        return DEFAULT_POLICY
    module = None
    if code_dir is not None:
        candidate = code_dir / vertical / "policy.py"
        if candidate.exists():
            from importlib.util import module_from_spec, spec_from_file_location

            spec = spec_from_file_location(f"{vertical}_policy", candidate)
            if spec and spec.loader:
                module = module_from_spec(spec)
                spec.loader.exec_module(module)  # type: ignore[attr-defined]
    if module is None:
        for name in (f"{vertical}.policy", f"code.{vertical}.policy"):
            try:
                module = import_module(name)
                break
            except ModuleNotFoundError:
                continue
    if module is None:
        return DEFAULT_POLICY
    policy = getattr(module, "POLICY", None)
    return policy if isinstance(policy, Policy) else DEFAULT_POLICY


# ---------------------------------------------------------------------------
# Relevance

def passes_relevance_gate(policy: Policy, source_type: str, feed_title: str, title: str, summary: str) -> bool:
    """False when a gated general source posts something off-topic."""
    if not policy.topic_terms or source_type not in policy.gated_source_types:
        return True
    if policy.exempt_source_pattern and policy.exempt_source_pattern.search(feed_title or ""):
        return True
    return bool(policy.topic_terms.search(f"{title}\n{summary}"))


# ---------------------------------------------------------------------------
# arXiv

ARXIV_ANNOUNCE_RE = re.compile(
    r"^\s*arXiv:\s*\S+\s+Announce Type:\s*(?P<kind>[\w-]+)\s*(?:\n|\s)*Abstract:\s*",
    re.IGNORECASE,
)


def arxiv_announce_type(summary: str) -> Optional[str]:
    """'new', 'replace', 'cross', 'replace-cross' — or None if not an arXiv item."""
    m = ARXIV_ANNOUNCE_RE.match(summary or "")
    return m.group("kind").lower() if m else None


# ---------------------------------------------------------------------------
# Summary boilerplate

_STRIP_PATTERNS: List[Pattern] = [
    ARXIV_ANNOUNCE_RE,
    # WordPress/Jetpack style trailers
    re.compile(r"\s*The post\b.*?\bappeared first on\b.*$", re.IGNORECASE | re.DOTALL),
    re.compile(r"\s*\bThis article\b.*?\b(first appeared|originally appeared|was first published)\b.*$", re.IGNORECASE | re.DOTALL),
    # "Read more", "Continue reading…" and their truncation markers
    re.compile(r"\s*(?:\[\s*)?(?:Read more|Read the full (?:story|article)|Continue reading|Keep reading|Full story)\b[^\n]*$", re.IGNORECASE),
    re.compile(r"\s*\[…\]\s*$|\s*\[\.\.\.\]\s*$"),
    # Hacker News feed metadata
    re.compile(r"\s*(?:Article URL|Comments URL|Points|# Comments)\s*:.*$", re.IGNORECASE | re.DOTALL),
]


def strip_summary_boilerplate(summary: str, title: str = "") -> str:
    """Remove feed boilerplate; return '' when the summary just repeats the title."""
    text = summary or ""
    for pattern in _STRIP_PATTERNS:
        text = pattern.sub("", text)
    text = re.sub(r"\s+", " ", text).strip("  -–—:;")
    if title:
        t = re.sub(r"\W+", " ", title.lower()).strip()
        s = re.sub(r"\W+", " ", text.lower()).strip()
        if s and (s == t or (len(s) <= len(t) + 20 and s.startswith(t))):
            return ""
    return text


# ---------------------------------------------------------------------------
# Dates

FUTURE_TOLERANCE = timedelta(hours=36)


def is_future_dated(published_ts: Optional[int], now: Optional[datetime] = None) -> bool:
    """Feeds occasionally publish with a bogus year; such items would sit on
    top of the feed forever, so the pipeline drops them."""
    if published_ts is None:
        return False
    now = now or datetime.now(timezone.utc)
    try:
        return datetime.fromtimestamp(published_ts, tz=timezone.utc) > now + FUTURE_TOLERANCE
    except (OverflowError, OSError, ValueError):
        return True


def is_aggregator(policy: Policy, feed_title: str) -> bool:
    return bool(policy.aggregator_pattern and policy.aggregator_pattern.search(feed_title or ""))


def any_in(terms: Iterable[str], text: str) -> bool:
    lower = (text or "").lower()
    return any(t.lower() in lower for t in terms)
