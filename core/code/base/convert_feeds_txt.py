#!/usr/bin/env python3
"""Convert feeds.txt into categorized OPML sections."""

from __future__ import annotations

import argparse
import re
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from path_utils import DEFAULT_FEED_FILENAMES, add_path_cli_arguments, load_path_config

SECTION_MAP: Dict[str, str] = {
    "AI, ML, Big Data News": "news",
    "AI, ML, Big Data Blogs": "blogs",
    "AI, ML, Big Data Podcasts": "podcasts",
    "AI, ML, Big Data Videos": "videos",
}

CATEGORY_ORDER = {
    "news": [
        "Official Labs & Research",
        "Agentic Frameworks & Tooling",
        "AI Platforms & Infra",
        "Curated AI Newsletters",
        "Research Explainability",
        "Data Science & MLOps",
        "Media & Tech Analysis",
        "Communities & Meta",
        "General News",
    ],
    "blogs": [
        "Company Engineering",
        "Practitioner Blogs",
        "Community Blogs",
        "Blogs",
    ],
    "podcasts": ["AI Podcasts", "Podcasts"],
    "videos": ["YouTube Creators", "Videos"],
}

DOMAIN_MAP = {
    "news": {
        "openai.com": "Official Labs & Research",
        "anthropic.com": "Official Labs & Research",
        "ai.googleblog.com": "Official Labs & Research",
        "deepmind.google": "Official Labs & Research",
        "ai.meta.com": "Official Labs & Research",
        "microsoft.com": "Official Labs & Research",
        "langchain": "Agentic Frameworks & Tooling",
        "llamaindex": "Agentic Frameworks & Tooling",
        "crewai": "Agentic Frameworks & Tooling",
        "autogpt": "Agentic Frameworks & Tooling",
        "semantic-kernel": "Agentic Frameworks & Tooling",
        "haystack": "Agentic Frameworks & Tooling",
        "cursor": "Agentic Frameworks & Tooling",
        "huggingface": "AI Platforms & Infra",
        "replicate": "AI Platforms & Infra",
        "vercel": "AI Platforms & Infra",
        "nvidia": "AI Platforms & Infra",
        "lightning.ai": "AI Platforms & Infra",
        "databricks": "AI Platforms & Infra",
        "anaconda": "AI Platforms & Infra",
        "jack-clark": "Curated AI Newsletters",
        "bensbites": "Curated AI Newsletters",
        "tldr.tech": "Curated AI Newsletters",
        "latentspace": "Curated AI Newsletters",
        "thesequence": "Curated AI Newsletters",
        "thegradient": "Research Explainability",
        "paperswithcode": "Research Explainability",
        "distill.pub": "Research Explainability",
        "bair.berkeley.edu": "Research Explainability",
        "eng.uber.com": "Data Science & MLOps",
        "netflixtechblog": "Data Science & MLOps",
        "airbnb": "Data Science & MLOps",
        "spotify": "Data Science & MLOps",
        "huyenchip": "Data Science & MLOps",
        "neptune.ai": "Data Science & MLOps",
        "wandb": "Data Science & MLOps",
        "cloud.google.com": "Data Science & MLOps",
        "reuters": "Media & Tech Analysis",
        "bloomberg": "Media & Tech Analysis",
        "wired": "Media & Tech Analysis",
        "theguardian": "Media & Tech Analysis",
        "theinformation": "Media & Tech Analysis",
        "semianalysis": "Media & Tech Analysis",
        "techcrunch": "Media & Tech Analysis",
        "venturebeat": "Media & Tech Analysis",
        "theregister": "Media & Tech Analysis",
        "theverge": "Media & Tech Analysis",
        "reddit": "Communities & Meta",
        "hnrss": "Communities & Meta",
    },
    "blogs": {
        "uber": "Company Engineering",
        "airbnb": "Company Engineering",
        "netflix": "Company Engineering",
        "spotify": "Company Engineering",
        "google": "Company Engineering",
        "meta": "Company Engineering",
        "microsoft": "Company Engineering",
        "anaconda": "Company Engineering",
        "neptune": "Company Engineering",
        "wandb": "Company Engineering",
        "databricks": "Company Engineering",
        "vercel": "Company Engineering",
        "replicate": "Company Engineering",
        "medium": "Practitioner Blogs",
        "substack": "Community Blogs",
        "langchain": "Practitioner Blogs",
        "llamaindex": "Practitioner Blogs",
    },
    "podcasts": {
        "twimlai": "AI Podcasts",
        "practicalai": "AI Podcasts",
        "gradient-dissent": "AI Podcasts",
        "chatgptreport": "AI Podcasts",
        "dataskeptic": "AI Podcasts",
        "dataengineeringpodcast": "AI Podcasts",
        "eyeonai": "AI Podcasts",
    },
    "videos": {
        "youtube": "YouTube Creators",
        "twominutepapers": "YouTube Creators",
        "yannic": "YouTube Creators",
        "sentdex": "YouTube Creators",
        "weightsandbiases": "YouTube Creators",
        "nvidia": "YouTube Creators",
    },
}

DEFAULT_CATEGORY = {
    "news": "General News",
    "blogs": "Blogs",
    "podcasts": "Podcasts",
    "videos": "Videos",
}

FEED_RE = re.compile(r"\(RSS feed:\s*(?P<url>[^)]+)\)?")


def parse_feeds_txt(path: Path) -> Dict[str, OrderedDict[str, List[Tuple[str, str]]]]:
    sections: Dict[str, OrderedDict[str, List[Tuple[str, str]]]] = {
        key: OrderedDict() for key in SECTION_MAP.values()
    }
    current_type: str | None = None
    current_category: Dict[str, str] = {key: DEFAULT_CATEGORY[key] for key in SECTION_MAP.values()}

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("⬆"):
                continue

            if line in SECTION_MAP:
                current_type = SECTION_MAP[line]
                continue

            if line.startswith("#") and current_type:
                current_category[current_type] = line.lstrip("#").strip()
                continue

            if "RSS feed:" not in line or not current_type:
                continue

            title, url = _parse_feed_line(line)
            if not title or not url:
                continue

            category = resolve_category(current_type, title, url, current_category[current_type])
            bucket = sections.setdefault(current_type, OrderedDict())
            bucket.setdefault(category, []).append((title, url))

    return sections


def resolve_category(feed_type: str, title: str, url: str, fallback: str) -> str:
    host = urlparse(url).netloc.lower()
    mapping = DOMAIN_MAP.get(feed_type, {})
    for pattern, label in mapping.items():
        if pattern in host or pattern in url.lower():
            return label
    return fallback or DEFAULT_CATEGORY.get(feed_type, feed_type.title())


def _parse_feed_line(line: str) -> Tuple[str, str]:
    match = FEED_RE.search(line)
    if not match:
        return "", ""
    url = match.group("url").strip()
    title = line[: match.start()].strip()
    title = title.rstrip("-– ")
    return title, url


def write_opml(output_path: Path, feed_type: str, categories: OrderedDict[str, List[Tuple[str, str]]]) -> None:
    from xml.etree.ElementTree import Element, SubElement, ElementTree

    root = Element("opml", version="2.0")
    head = SubElement(root, "head")
    title_el = SubElement(head, "title")
    title_el.text = feed_type.title()

    body = SubElement(root, "body")
    order = CATEGORY_ORDER.get(feed_type, [])
    for category in order:
        if category not in categories:
            continue
        feeds = categories[category]
        group = SubElement(body, "outline", title=category, text=category)
        for name, url in feeds:
            SubElement(
                group,
                "outline",
                type="rss",
                title=name,
                text=name,
                xmlUrl=url,
                htmlUrl=url,
            )

    _indent_xml(root)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree = ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def _indent_xml(elem, level: int = 0) -> None:
    indent = "\n" + level * "    "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "    "
        for child in elem:
            _indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = indent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert source/<vertical>/feeds.txt into categorized OPML sections.")
    add_path_cli_arguments(parser)
    parser.add_argument(
        "--feeds-file",
        type=Path,
        help="Explicit path to feeds.txt. Defaults to source/<vertical>/feeds.txt.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path_config = load_path_config(start=__file__, base_dir=args.base_dir, data_dir=args.data_dir, vertical=args.vertical)

    feeds_txt = args.feeds_file or (path_config.source_dir / "feeds.txt")
    if not feeds_txt.exists():
        raise SystemExit(f"feeds.txt not found: {feeds_txt}")

    sections = parse_feeds_txt(feeds_txt)

    for feed_type, filename in DEFAULT_FEED_FILENAMES.items():
        categories = sections.get(feed_type)
        if not categories:
            continue
        output_path = path_config.source_dir / filename
        write_opml(output_path, feed_type, categories)
        total = sum(len(feeds) for feeds in categories.values())
        print(f"[OK] Wrote {total} feeds to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
