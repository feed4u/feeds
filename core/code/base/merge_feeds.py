#!/usr/bin/env python3
"""
Merge vertical-specific feed files into a single OPML manifest.

Expected files inside source/<vertical>/:
  - news.xml
  - blog.xml
  - podcasts.xml
  - videos.xml

The combined file is written to feeds.xml so the ingestion pipeline
can keep using a single OPML entry point.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from typing import Iterable, List

from path_utils import DEFAULT_FEED_FILENAMES, add_path_cli_arguments, load_path_config

SECTION_ORDER = ["news", "blogs", "podcasts", "videos"]


def indent(elem: ET.Element, level: int = 0) -> None:
    """Pretty print XML in-place with 4-space indentation."""
    i = "\n" + level * "    "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "    "
        for child in elem:
            indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = i + "    "
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = i
    else:
        if not elem.text or not elem.text.strip():
            elem.text = ""
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i


def load_section(path: Path) -> Iterable[ET.Element]:
    tree = ET.parse(path)
    body = tree.find("body")
    if body is None:
        raise ValueError(f"{path} is missing a <body> element")
    return [deepcopy(outline) for outline in body.findall("outline")]


def build_combined_tree(sections: List[ET.Element]) -> ET.ElementTree:
    root = ET.Element("opml", version="2.0")
    head = ET.SubElement(root, "head")
    title = ET.SubElement(head, "title")
    title.text = "Security News Feeds"
    body = ET.SubElement(root, "body")

    for outline in sections:
        body.append(outline)

    indent(root)
    return ET.ElementTree(root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge news/blog/podcasts XMLs into feeds.xml"
    )
    add_path_cli_arguments(parser)
    parser.add_argument(
        "--sections",
        nargs="+",
        default=SECTION_ORDER,
        help="Section files to merge (default: news blogs podcasts)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path_config = load_path_config(
        start=__file__,
        base_dir=args.base_dir,
        vertical=args.vertical,
        opml_path=args.opml_path,
        source_dir=None,
    )
    source_dir = path_config.source_dir

    outlines: List[ET.Element] = []
    for slug in args.sections:
        filename = DEFAULT_FEED_FILENAMES.get(slug, f"{slug}.xml")
        section_file = source_dir / filename
        if not section_file.exists():
            print(f"[WARN] Section missing: {section_file}", file=sys.stderr)
            continue
        outlines.extend(load_section(section_file))

    if not outlines:
        print("[ERROR] No feed sections found. Nothing to merge.", file=sys.stderr)
        return 1

    tree = build_combined_tree(outlines)
    output_path = path_config.opml_path
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    print(f"[INFO] Merged {len(outlines)} sections into {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
