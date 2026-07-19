"""HTML sanitization, date parsing, and OPML processing."""

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable, Optional, Set, Tuple

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore


def clean_html_summary(
    raw: str,
    allowed_tags: Set[str],
    allowed_attrs: dict,
    allowed_href_prefixes: tuple,
) -> Tuple[str, str]:
    """
    Clean HTML summary and return both plain text and sanitized HTML.

    Args:
        raw: Raw HTML content
        allowed_tags: Set of allowed HTML tags
        allowed_attrs: Dict of allowed attributes per tag
        allowed_href_prefixes: Tuple of allowed href prefixes

    Returns:
        Tuple of (plain_text, sanitized_html)
    """
    if not raw:
        return "", ""

    raw = html.unescape(raw)

    # Fallback plain text extraction
    text_fallback = re.sub(r"<[^>]+>", " ", raw)
    text_fallback = re.sub(r"\s+", " ", text_fallback).strip()

    if BeautifulSoup is None:
        return text_fallback, ""

    soup = BeautifulSoup(raw, "html.parser")

    # Remove script and style tags
    for tag in soup(["script", "style"]):
        tag.decompose()

    # Filter tags and attributes
    for tag in soup.find_all(True):
        tag_name = tag.name.lower()

        if tag_name not in allowed_tags:
            tag.unwrap()
            continue

        # Filter attributes
        tag_allowed_attrs = allowed_attrs.get(tag_name, set())
        for attr in list(tag.attrs):
            if attr not in tag_allowed_attrs:
                del tag[attr]

        # Validate href
        if tag_name == "a":
            href = tag.get("href")
            if href and not _is_safe_href(href, allowed_href_prefixes):
                tag.unwrap()
                continue
            if href:
                tag["href"] = href.strip()

    # Extract text
    text = soup.get_text(separator=" ", strip=True)

    # Extract sanitized HTML
    if soup.body:
        html_output = "".join(str(child) for child in soup.body.contents).strip()
    else:
        html_output = str(soup).strip()

    return text or text_fallback, html_output


def _is_safe_href(href: str, allowed_prefixes: tuple) -> bool:
    """Check if href is safe based on allowed prefixes."""
    href = (href or "").strip()
    if not href:
        return False

    href_lower = href.lower()
    return (
        href_lower.startswith(allowed_prefixes)
        or href.startswith("/")
        or href.startswith("#")
    )


def parse_published_date(entry) -> Optional[datetime]:
    """
    Parse published date from feed entry.

    Args:
        entry: Feedparser entry object

    Returns:
        Timezone-aware datetime or None
    """
    # Try feedparser's parsed fields first
    dt_struct = getattr(entry, "published_parsed", None) or getattr(
        entry, "updated_parsed", None
    )

    if dt_struct is not None:
        try:
            dt = datetime(*dt_struct[:6])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

    # Try common date fields
    candidate_fields = [
        "published",
        "updated",
        "pubDate",
        "dc:date",
        "dc_date",
        "date",
    ]

    for field in candidate_fields:
        value = getattr(entry, field, None)
        if not value and isinstance(entry, dict):
            value = entry.get(field)
        if not value:
            continue

        try:
            dt = parsedate_to_datetime(str(value))
        except (TypeError, ValueError):
            continue

        if dt is None:
            continue

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    return None


def parse_opml_feeds(opml_path: Path) -> Iterable[Tuple[str, str, str]]:
    """
    Parse OPML file and yield (group_title, feed_title, xml_url) tuples.

    Supports arbitrarily nested outline structures by carrying the most recent
    non-feed group's title as the category label.
    """
    tree = ET.parse(opml_path)
    root = tree.getroot()
    body = root.find("body")

    if body is None:
        return

    def _walk(node: ET.Element, current_label: str) -> Iterable[Tuple[str, str, str]]:
        for outline in node.findall("outline"):
            xml_url = outline.attrib.get("xmlUrl")
            title = outline.attrib.get("title") or outline.attrib.get("text") or current_label

            if xml_url:
                yield current_label or "General", title, xml_url
            else:
                next_label = title or current_label or "General"
                yield from _walk(outline, next_label)

    yield from _walk(body, "General")


def slugify(label: str) -> str:
    """Convert label to slug format."""
    text = label.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "unknown"
