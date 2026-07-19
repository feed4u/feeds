"""Dynamic category loading from OPML file."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple


def slugify(label: str) -> str:
    """
    Convert label to slug format.

    Args:
        label: Category label

    Returns:
        Slugified string
    """
    text = label.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "unknown"


def load_categories_from_opml(opml_path: Path) -> Dict[str, str]:
    """
    Dynamically load category mappings from OPML file.

    Extracts all group titles and generates slug mappings automatically.
    This eliminates the need to manually update Python code when
    categories change in the OPML file.

    Args:
        opml_path: Path to OPML file

    Returns:
        Dict mapping category label to slug

    Example:
        {
            "Crypto & Blockchain Security": "crypto-blockchain-security",
            "DFIR & Forensics": "dfir-forensics",
            ...
        }
    """
    if not opml_path.exists():
        raise FileNotFoundError(f"OPML file not found: {opml_path}")

    tree = ET.parse(opml_path)
    root = tree.getroot()
    body = root.find("body")

    if body is None:
        return {}

    category_map: Dict[str, str] = {}

    # Extract all group titles
    for group in body.findall("outline"):
        title = group.attrib.get("title") or group.attrib.get("text")
        if title:
            title = title.strip()
            slug = slugify(title)
            category_map[title] = slug

    return category_map


def get_category_groups(opml_path: Path) -> List[Tuple[str, str]]:
    """
    Get list of (category_label, category_slug) tuples from OPML.

    Args:
        opml_path: Path to OPML file

    Returns:
        List of (label, slug) tuples sorted by label
    """
    category_map = load_categories_from_opml(opml_path)
    return sorted(category_map.items())


class CategoryMapper:
    """Category mapper with caching for performance."""

    def __init__(self, feed_files: Dict[str, Path], fallback_opml: Path):
        """
        Initialize category mapper.

        Args:
            feed_files: Mapping of feed types to OPML files
            fallback_opml: Fallback OPML path if feed_files missing
        """
        self.feed_files = feed_files or {"news": fallback_opml}
        self.fallback_opml = fallback_opml
        self._cache: Dict[str, str] = {}
        self._category_types: Dict[str, str] = {}
        self._loaded = False

    def load(self) -> None:
        """Load categories from OPML (with caching)."""
        if not self._loaded:
            self._cache = {}
            self._category_types = {}
            for feed_type, path in self.feed_files.items():
                try:
                    category_map = load_categories_from_opml(path)
                except FileNotFoundError:
                    continue
                for label, slug in category_map.items():
                    self._cache[label] = slug
                    self._category_types[label] = feed_type

            if not self._cache:
                self._cache = load_categories_from_opml(self.fallback_opml)
            self._loaded = True

    def get_slug(self, label: str) -> str:
        """
        Get slug for category label.

        Args:
            label: Category label

        Returns:
            Category slug (auto-generated if not in cache)
        """
        self.load()

        # Try exact match first
        if label in self._cache:
            return self._cache[label]

        # Fall back to auto-generating slug
        return slugify(label)

    def get_all(self) -> Dict[str, str]:
        """Get all category mappings."""
        self.load()
        return dict(self._cache)

    def get_category_type(self, label: str, default: str = "news") -> str:
        """Return the top-level feed type associated with a category."""
        self.load()
        return self._category_types.get(label, default)
