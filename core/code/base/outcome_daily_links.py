#!/usr/bin/env python3
"""
outcome_daily_links.py - score the daily briefing's links on one frozen real day.

The Agent Console outcome check runs this once per declared input, offline and
without credentials. It replays one frozen day through the scored checkout's
own ``daily_briefing.run()`` and checks every link the briefing emits against
an independent reference built from the day's source records.

Measured slice (and only this): source-link and date integrity of the
topics-mode daily briefing on its no-reply path. The model's raw reply was
never saved, so the replay answers every model call with an unusable reply and
the briefing falls back to the topics' own ranking for its sections. That runs
the real loading and deduplication of the day's items, item numbering,
topic-to-item resolution, link cleaning, markdown rendering, highlights and
the report writer. It does not measure the editor's choice of sections, the
headline text, editorial quality or the web page's TypeScript rendering.

Items: every link occurrence the report emits.
    - a markdown link: http(s), in the reference dated on the analysis day,
      and one of the stories of the topic its section stands for (headline
      links: one of the headline's own links);
    - a top-story / headline link: the same, against the section's topic;
    - a highlight: its link passes as above, it is cited by a section or the
      headline, and its ``published`` falls on the reference's UTC date.
Score = passing items / items. The topics file is frozen input, never truth:
it only says which stories a section may cite.

Exit contract (stdout carries nothing but the score object):
    0  {"score": <0..1>, "items": <n>}
    2  unknown: the environment, input or reference is missing or malformed
    4  refused: the scored checkout crashed or emitted nothing to score
Zero emitted links is a refusal, never a perfect empty score.

Freezing an input (operator, once, into the private directory):
    python3 core/code/base/outcome_daily_links.py freeze --vertical 4u \\
        --date 2026-10-20 --archive-dir core/data/4u/archive \\
        --source-commit <origin/main sha> --out <private dir>/4u-2026-10-20
writes ``input.json``, ``reference.json`` and ``manifest.json`` (hashes and
provenance). The reference is read from each source item's ``published``
string without any briefing code. The outcome declaration then names them:
    {"repository": "feeds",
     "inputs": [{"input": "4u-2026-10-20/input.json",
                 "reference": "4u-2026-10-20/reference.json"}],
     "scorer": ["python3", "-I", "-B", "core/code/base/outcome_daily_links.py"],
     "threshold": 1.0, "timeoutSeconds": 300}
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse

sys.dont_write_bytecode = True  # the scored checkout stays clean

INPUT_FORMAT = "daily-links-input/1"
REFERENCE_FORMAT = "daily-links-reference/1"
MANIFEST_FORMAT = "daily-links-manifest/1"
EXIT_UNKNOWN = 2
EXIT_REFUSED = 4
FEED_TYPE_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
MD_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
CHECKOUT_ROOT = Path(__file__).resolve().parents[3]


class Unknown(Exception):
    """No score: the environment, input or reference cannot be read as one."""


class Refused(Exception):
    """No score: the scored checkout gave nothing that can be scored."""


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #

def _private_path(name: str, environ: Dict[str, str]) -> Path:
    value = environ.get(name, "")
    if not value: raise Unknown(f"{name} is not set")  # guard: env-missing
    path = Path(value)
    if not path.is_absolute(): raise Unknown(f"{name} is not absolute")  # guard: path-relative
    if ".." in path.parts: raise Unknown(f"{name} traverses upwards")  # guard: path-traversal
    if any(p.is_symlink() for p in (path, *path.parents)): raise Unknown(f"{name} goes through a symlink")  # guard: path-symlink
    return path


def _checkout(environ: Dict[str, str]) -> Path:
    value = environ.get("AGENT_CONSOLE_OUTCOME_CHECKOUT", "")
    path = Path(value)
    if not value or not path.is_absolute(): raise Unknown("checkout is not an absolute path")  # guard: checkout-path
    if not (path / "core" / "code" / "base" / "daily_briefing.py").is_file(): raise Unknown("checkout has no daily_briefing.py")  # guard: checkout-code
    return path.resolve()


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _read_json(path: Path, what: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Unknown(f"{what} is unreadable: {exc.__class__.__name__}") from exc  # guard: unreadable


def _day(value: Any) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise Unknown(f"not a day: {value!r}") from exc  # guard: bad-day


def load_input(path: Path) -> Dict[str, Any]:
    bundle = _read_json(path, "input")
    if not isinstance(bundle, dict) or bundle.get("format") != INPUT_FORMAT: raise Unknown("input is not a daily-links input")  # guard: input-format
    if not isinstance(bundle.get("daily"), dict) or not bundle["daily"]: raise Unknown("input has no daily files")  # guard: input-daily
    if not isinstance(bundle.get("topics"), dict) or not isinstance(bundle["topics"].get("topics"), list): raise Unknown("input has no topics")  # guard: input-topics
    for feed_type in bundle["daily"]:
        if not FEED_TYPE_RE.match(feed_type): raise Unknown("input names an unsafe feed type")  # guard: member-name
    _day(bundle.get("date"))
    return bundle


def load_reference(path: Path, bundle: Dict[str, Any]) -> Dict[str, str]:
    reference = _read_json(path, "reference")
    if not isinstance(reference, dict) or reference.get("format") != REFERENCE_FORMAT or not isinstance(reference.get("links"), dict): raise Unknown("reference is not a daily-links reference")  # guard: reference-format
    if (reference.get("vertical"), reference.get("date")) != (bundle.get("vertical"), bundle.get("date")): raise Unknown("reference is for another vertical or day")  # guard: reference-foreign
    return {str(k): str(v) for k, v in reference["links"].items()}


# --------------------------------------------------------------------------- #
# Replay
# --------------------------------------------------------------------------- #

class ReplayClient:
    """Stands in for the LLM: reachable, but never with a usable reply.

    No network: the briefing takes its documented fallback, sections in the
    topics' own ranking.
    """

    def __init__(self, llm_error: type):
        self._error = llm_error
        self.config = type("ReplayConfig", (), {"model": "replay-no-reply", "base_url": "replay://offline"})()

    def check_available(self, timeout: float = 10.0) -> None:
        return None

    def chat_json(self, messages: Any, **kwargs: Any) -> Any:
        raise self._error("replay: the original model reply was not saved")


def materialize(bundle: Dict[str, Any], workdir: Path) -> Path:
    """Write the frozen day as the archive layout daily_briefing reads."""
    archive = workdir / "archive"
    for feed_type, payload in bundle["daily"].items():
        target = archive / feed_type / "daily" / f"{bundle['date']}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    topics = archive / "news" / "topics" / f"{bundle['date']}.json"
    topics.parent.mkdir(parents=True, exist_ok=True)
    topics.write_text(json.dumps(bundle["topics"], ensure_ascii=False), encoding="utf-8")
    return archive


def replay(checkout: Path, bundle: Dict[str, Any], scratch: Path) -> Dict[str, Any]:
    """Run the scored checkout's daily_briefing.run() on the frozen day."""
    sys.path.insert(0, str(checkout / "core" / "code" / "base"))
    workdir = Path(tempfile.mkdtemp(prefix="replay-", dir=scratch))
    archive = materialize(bundle, workdir)
    day = _day(bundle["date"])
    try:
        with contextlib.redirect_stdout(sys.stderr):
            import daily_briefing
            from llm_client import LLMError

            written = daily_briefing.run(
                archive_dir=archive,
                vertical=str(bundle.get("vertical") or ""),
                day=day,
                client=ReplayClient(LLMError),
            )
    except Exception as exc:
        raise Refused(f"the scored checkout failed: {exc.__class__.__name__}") from exc  # guard: scored-crash
    report_path = archive / f"daily_report_{day.isoformat()}.json"
    if written is None or not report_path.is_file(): raise Refused("the scored checkout wrote no report")  # guard: output-missing
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refused("the report is not JSON") from exc  # guard: output-not-json
    if not isinstance(report, dict): raise Refused("the report is not an object")  # guard: output-malformed
    return report


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #

def _markdown_form(link: str) -> str:
    # The page's markdown subset cannot carry ")" or a space inside a link.
    return link.replace(")", "%29").replace(" ", "%20")


def _utc_day(value: Any) -> Optional[str]:
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        return None
    return stamp.astimezone(timezone.utc).date().isoformat()


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def score_report(report: Dict[str, Any], bundle: Dict[str, Any], reference: Dict[str, str]) -> Tuple[int, int]:
    """(passing items, items) for one report against the frozen source."""
    day = str(bundle["date"])
    topic_links: Dict[Any, Set[str]] = {}
    for topic in bundle["topics"]["topics"]:
        if isinstance(topic, dict):
            topic_links[topic.get("id")] = {
                s.get("link") for s in _list(topic.get("stories")) if isinstance(s, dict)
            }

    def sourced(link: Any) -> bool:
        if not isinstance(link, str):
            return False
        parsed = urlparse(link)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc) and reference.get(link) == day

    passed = total = 0

    def check(ok: bool) -> None:
        nonlocal passed, total
        total += 1
        passed += bool(ok)

    headline = [e for e in _list(report.get("headline")) if isinstance(e, dict)]
    sections = [s for s in _list(report.get("top_stories")) if isinstance(s, dict)]
    headline_links = {link for e in headline for link in _list(e.get("links")) if isinstance(link, str)}
    allowed_by_section = [topic_links.get(s.get("topic_id"), set()) for s in sections]

    for link in headline_links:
        check(sourced(link))
    for section, allowed in zip(sections, allowed_by_section):
        for link in _list(section.get("links")):
            check(sourced(link) and link in allowed)

    # Markdown: an optional headline block, then one ### block per section.
    blocks: List[List[str]] = []
    for line in str(report.get("daily_report_markdown") or "").splitlines():
        if line.startswith("### "):
            blocks.append([])
        elif blocks:
            blocks[-1].extend(MD_LINK_RE.findall(line))
    allowed_blocks = ([headline_links] if headline else []) + allowed_by_section
    for index, block in enumerate(blocks):
        allowed = allowed_blocks[index] if index < len(allowed_blocks) else set()
        by_form = {_markdown_form(link): link for link in allowed}
        for emitted in block:
            check(emitted in by_form and sourced(by_form[emitted]))

    cited = headline_links | {
        link for s in sections for link in _list(s.get("links")) if isinstance(link, str)
    }
    for item in _list(report.get("highlights")):
        link = item.get("link") if isinstance(item, dict) else None
        published = item.get("published") if isinstance(item, dict) else None
        check(sourced(link) and link in cited and _utc_day(published) == reference.get(link))
    return passed, total


def score(environ: Dict[str, str]) -> Dict[str, Any]:
    input_path = _private_path("AGENT_CONSOLE_OUTCOME_INPUT", environ)
    reference_path = _private_path("AGENT_CONSOLE_OUTCOME_REFERENCE", environ)
    scratch = _private_path("AGENT_CONSOLE_OUTCOME_SCRATCH", environ)
    checkout = _checkout(environ)
    if reference_path.parent != input_path.parent: raise Unknown("reference is not frozen beside its input")  # guard: path-foreign
    for path in (input_path, reference_path, scratch):
        if _within(path, checkout): raise Unknown("a private path lies inside the scored checkout")  # guard: path-in-checkout
    if not scratch.is_dir(): raise Unknown("scratch is not a directory")  # guard: scratch-dir
    bundle = load_input(input_path)
    reference = load_reference(reference_path, bundle)
    report = replay(checkout, bundle, scratch)
    passed, total = score_report(report, bundle, reference)
    if total == 0: raise Refused("the report emitted no links")  # guard: no-links
    return {"score": round(passed / max(total, 1), 6), "items": total}


# --------------------------------------------------------------------------- #
# Freeze
# --------------------------------------------------------------------------- #

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def freeze(archive_dir: Path, vertical: str, day: date, out: Path, source_commit: str) -> Dict[str, Any]:
    """Copy one real day out of the archive into a frozen input + reference."""
    if _within(out, CHECKOUT_ROOT): raise Unknown("refusing to freeze into the checkout, where it could be committed")  # guard: freeze-into-checkout
    names = ("input.json", "reference.json", "manifest.json")
    if any((out / name).exists() for name in names): raise Unknown("refusing to overwrite a frozen input")  # guard: freeze-overwrite
    day_str = day.isoformat()
    daily: Dict[str, Any] = {}
    sources: Dict[str, str] = {}
    links: Dict[str, str] = {}
    unparsed = 0
    for path in sorted(archive_dir.glob(f"*/daily/{day_str}.json")):
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        daily[path.parent.parent.name] = payload
        sources[path.relative_to(archive_dir).as_posix()] = _sha256(raw)
        rows = payload.get("items", []) if isinstance(payload, dict) else payload
        for row in rows or []:
            if not isinstance(row, dict) or not row.get("link"):
                continue
            published = _utc_day(row.get("published"))
            if published is None:
                unparsed += 1
            elif links.setdefault(row["link"], published) != published:
                links[row["link"]] = "conflicting"
    topics_file = archive_dir / "news" / "topics" / f"{day_str}.json"
    if not daily or not topics_file.is_file(): raise Unknown(f"no daily files and topics for {vertical} {day_str} in the archive")  # guard: freeze-empty
    topics_raw = topics_file.read_bytes()
    sources[topics_file.relative_to(archive_dir).as_posix()] = _sha256(topics_raw)
    bundle = {"format": INPUT_FORMAT, "vertical": vertical, "date": day_str,
              "daily": daily, "topics": json.loads(topics_raw.decode("utf-8"))}
    reference = {"format": REFERENCE_FORMAT, "vertical": vertical, "date": day_str,
                 "basis": "UTC date of each source item's published string", "links": links}
    input_bytes = (json.dumps(bundle, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    reference_bytes = (json.dumps(reference, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    manifest = {
        "format": MANIFEST_FORMAT, "vertical": vertical, "date": day_str,
        "source_commit": source_commit, "sources": sources,
        "input_sha256": _sha256(input_bytes), "reference_sha256": _sha256(reference_bytes),
        "reference_links": len(links), "unparsed_dates": unparsed,
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "input.json").write_bytes(input_bytes)
    (out / "reference.json").write_bytes(reference_bytes)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: Optional[Sequence[str]] = None, environ: Optional[Dict[str, str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    environ = dict(os.environ if environ is None else environ)
    try:
        if argv[:1] == ["freeze"]:
            parser = argparse.ArgumentParser(prog="outcome_daily_links.py freeze")
            parser.add_argument("--vertical", required=True)
            parser.add_argument("--date", required=True)
            parser.add_argument("--archive-dir", required=True, type=Path)
            parser.add_argument("--out", required=True, type=Path)
            parser.add_argument("--source-commit", default="unrecorded")
            args = parser.parse_args(argv[1:])
            manifest = freeze(args.archive_dir, args.vertical, _day(args.date), args.out, args.source_commit)
            print(json.dumps({k: manifest[k] for k in ("input_sha256", "reference_sha256", "reference_links")}))
            return 0
        if argv:
            raise Unknown("usage: outcome_daily_links.py [freeze ...]")
        result = score(environ)
    except Unknown as exc:
        print(f"[UNKNOWN] {exc}", file=sys.stderr)
        return EXIT_UNKNOWN
    except Refused as exc:
        print(f"[REFUSED] {exc}", file=sys.stderr)
        return EXIT_REFUSED
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
