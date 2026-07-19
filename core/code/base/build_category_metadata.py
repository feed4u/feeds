#!/usr/bin/env python3
"""
Generate category metadata JSON for the web app from OPML sources.

Prefers sectional files under `source/<vertical>/*.xml` (news/blogs/podcasts)
and falls back to a single merged `feeds.xml` when section files are missing.

Output (matches web expectations):
- generated_at: ISO timestamp
- source: string path to source directory or OPML
- total_categories: number
- slug_to_label: Record<slug, label>
- categories: Array<{id, label, slug}>
- feed_types?: string[]
- hierarchy?: Record<feed_type, FeedCategory[]>
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

from path_utils import add_path_cli_arguments, load_path_config


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def load_categories_from_opml(opml_path: Path) -> Dict[str, str]:
    """Fallback loader for legacy single OPML files."""
    tree = ET.parse(opml_path)
    root = tree.getroot()
    body = root.find("body")
    if body is None:
        return {}

    category_map: Dict[str, str] = {}
    for group in body.findall("outline"):
        title = (group.attrib.get("title") or group.attrib.get("text") or "").strip()
        if not title:
            continue
        category_map[title] = slugify(title)
    return category_map


def parse_feed_sections(feed_files: Dict[str, Path]) -> Tuple[Dict[str, str], Dict[str, List[dict]]]:
    """Parse sectional OPML files and return slug mappings + hierarchy."""
    hierarchy: Dict[str, List[dict]] = {}
    slug_map: Dict[str, str] = {}

    for feed_type, path in feed_files.items():
        if not path.exists():
            continue

        tree = ET.parse(path)
        root = tree.getroot()
        body = root.find("body")
        if body is None:
            continue

        sections: List[dict] = []
        for group in body.findall("outline"):
            title = (group.attrib.get("title") or group.attrib.get("text") or "").strip()
            if not title:
                continue
            slug = slugify(title)
            slug_map[title] = slug

            feeds = []
            for feed in group.findall("outline"):
                feed_title = (feed.attrib.get("title") or feed.attrib.get("text") or "").strip()
                if not feed_title:
                    continue
                feeds.append(
                    {
                        "title": feed_title,
                        "xml_url": feed.attrib.get("xmlUrl", "").strip(),
                        "html_url": feed.attrib.get("htmlUrl", "").strip(),
                    }
                )

            sections.append(
                {
                    "label": title,
                    "slug": slug,
                    "feeds": feeds,
                }
            )

        hierarchy[feed_type] = sections

    return slug_map, hierarchy


def generate_category_metadata(
    feed_files: Dict[str, Path], merged_opml: Path, output_path: Path
) -> None:
    """Generate category metadata JSON that the frontend expects."""
    print(f"[INFO] Loading categories from {len(feed_files)} feed sections...")
    slug_map, hierarchy = parse_feed_sections(feed_files)

    used_source: str
    if not slug_map and merged_opml.exists():
        # Fallback to merged OPML if sectional files missing
        slug_map = load_categories_from_opml(merged_opml)
        used_source = str(merged_opml)
    else:
        used_source = str(merged_opml.parent)

    print(f"[INFO] Found {len(slug_map)} categories across {len(hierarchy)} sections")

    # Build mappings and arrays per web/src/data/newsData.ts interface
    slug_to_label: Dict[str, str] = {slug: label for label, slug in slug_map.items()}
    categories_array: List[Dict[str, str]] = [
        {"id": slug, "label": label, "slug": slug}
        for label, slug in slug_map.items()
    ]
    categories_array.sort(key=lambda x: x["label"])  # deterministic order

    from datetime import datetime, timezone
    metadata: Dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": used_source,
        "total_categories": len(categories_array),
        "slug_to_label": slug_to_label,
        "categories": categories_array,
    }

    if hierarchy:
        metadata["feed_types"] = list(feed_files.keys())
        metadata["hierarchy"] = hierarchy

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"[OK] Category metadata written to {output_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate category metadata JSON from the current vertical's feeds."
    )
    add_path_cli_arguments(parser)
    return parser.parse_args()


def main():
    args = _parse_args()
    path_config = load_path_config(
        start=__file__,
        base_dir=args.base_dir,
        data_dir=args.data_dir,
        vertical=args.vertical,
        opml_path=args.opml_path,
    )
    opml_path = path_config.opml_path
    feed_files = path_config.feed_files
    output_path = args.output_path or (path_config.data_dir / "category_metadata.json")

    missing = [path for path in feed_files.values() if not path.exists()]
    if missing:
        print("[WARN] Missing feed sections:")
        for path in missing:
            print(f"  - {path}")

    if not opml_path.exists() and not feed_files:
        print(f"[ERROR] No OPML sources found under {path_config.source_dir}")
        sys.exit(1)

    generate_category_metadata(feed_files, opml_path, output_path)


if __name__ == "__main__":
    main()
