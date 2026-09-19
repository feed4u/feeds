"""Smart group (topic) classification.

Rules are matched on word boundaries, so ``elt`` no longer fires on *felt*,
``sota`` on *Minnesota* or ``valuation`` on *evaluation*. A rule is either the
classic ``(name, [keywords])`` tuple (any keyword matches) or
``(name, {"any": [...], "require": [...], "title": True})`` where at least
one term from *each* list must match — e.g. a "Model releases" rule that
needs both a release verb and a model name — and ``"title": True`` restricts
the rule to the title (summaries mention everything).

Keyword syntax: plain words or phrases; a trailing ``*`` matches any
continuation (``robot*`` → robots, robotics). Terms that start or end with a
non-alphanumeric character (``cve-``, ``/r/``) only get a boundary on the
alphanumeric side.

``summary_mode`` decides how much the summary counts:

* ``"always"`` (default): title matches first, then summary matches, capped.
* ``"fallback"``: the title decides; the summary is consulted only when the
  title matched no rule, and then contributes at most two tags. Summaries
  mention everything ("…while Nvidia chips power the data centers that…"),
  so this is far more precise — on 1,789 AI headlines it cut three-tag items
  from 41% to 1% while leaving 85% tagged. Verticals opt in via their policy.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Mapping, Sequence, Tuple, Union

from .smart_groups import get_smart_group_rules

RuleSpec = Union[Sequence[str], Mapping[str, Sequence[str]]]
Rule = Tuple[str, RuleSpec]

DEFAULT_MAX_GROUPS = 3
SUMMARY_FALLBACK_MAX = 2

_compiled_cache: dict = {}


def compile_term(term: str) -> re.Pattern:
    """Compile one keyword into a boundary-aware, case-insensitive regex."""
    cached = _compiled_cache.get(term)
    if cached is not None:
        return cached
    raw = term.strip()
    prefix_wild = raw.endswith("*")
    if prefix_wild:
        raw = raw[:-1]
    raw = re.sub(r"\s+", " ", raw.lower())
    body = re.escape(raw).replace(r"\ ", r"\s+")
    lead = r"(?<![a-z0-9])" if raw[:1].isalnum() else ""
    trail = "" if prefix_wild or not raw[-1:].isalnum() else r"(?![a-z0-9])"
    pattern = re.compile(lead + body + trail, re.IGNORECASE)
    _compiled_cache[term] = pattern
    return pattern


def _matches_any(terms: Iterable[str], text: str) -> bool:
    return any(compile_term(t).search(text) for t in terms)


def rule_matches(spec: RuleSpec, text: str) -> bool:
    """True if the rule fires on ``text``."""
    if isinstance(spec, Mapping):
        any_terms = spec.get("any") or []
        require = spec.get("require") or []
        if any_terms and not _matches_any(any_terms, text):
            return False
        if require and not _matches_any(require, text):
            return False
        return bool(any_terms or require)
    return _matches_any(spec, text)


def classify_smart_groups(
    title: str,
    summary: str = "",
    rules: Sequence[Rule] | None = None,
    *,
    max_groups: int = DEFAULT_MAX_GROUPS,
    fallback_text: str = "",
    summary_mode: str = "always",
) -> List[str]:
    """
    Classify one item into smart groups.

    Args:
        title: Item title (matches here rank highest).
        summary: Plain-text summary.
        rules: Pre-loaded rules; defaults to the base rule set.
        max_groups: Cap on tags per item (0 = unlimited).
        fallback_text: Extra text (e.g. the feed title) consulted only when
            title and summary produced nothing.
        summary_mode: "always" or "fallback" (see module docstring).

    Returns:
        Ordered, de-duplicated list of group names.
    """
    smart_group_rules = rules or get_smart_group_rules()
    title = title or ""
    summary = summary or ""
    combined = f"{title}\n{summary}"

    names: List[str] = []

    for name, spec in smart_group_rules:
        if rule_matches(spec, title) and name not in names:
            names.append(name)
    title_matched = bool(names)
    if title_matched and summary_mode == "fallback":
        return names[:max_groups] if max_groups else names

    for name, spec in smart_group_rules:
        title_only = isinstance(spec, Mapping) and bool(spec.get("title"))
        if not title_only and rule_matches(spec, combined) and name not in names:
            names.append(name)
    if names:
        if summary_mode == "fallback":
            cap = min(max_groups, SUMMARY_FALLBACK_MAX) if max_groups else SUMMARY_FALLBACK_MAX
            return names[:cap]
        return names[:max_groups] if max_groups else names

    if fallback_text:
        for name, spec in smart_group_rules:
            if rule_matches(spec, fallback_text) and name not in names:
                names.append(name)
    return names[:max_groups] if max_groups else names
