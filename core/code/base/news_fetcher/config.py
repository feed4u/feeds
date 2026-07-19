"""Configuration helpers for the news fetcher."""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Set, Tuple

from path_utils import PathConfig, load_path_config

# Runtime configuration
DAYS_BACK = int(os.environ.get("DAYS_BACK", "30"))
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "10"))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "25"))

# HTML sanitization
SUMMARY_ALLOWED_TAGS: Set[str] = {
    "a", "p", "ul", "ol", "li", "br", "strong", "em", "b", "i",
    "code", "pre", "blockquote", "span", "div",
}

SUMMARY_ALLOWED_ATTRS: Dict[str, Set[str]] = {
    "a": {"href"},
}

SUMMARY_ALLOWED_HREF_PREFIXES: Tuple[str, ...] = (
    "http://", "https://", "mailto:", "#", "/", "//"
)

# Curated keywords
CURATED_KEYWORDS: List[str] = [
    "zero-day", "zeroday", "0day", "critical vulnerability", "exploit",
    "rce", "remote code execution", "privilege escalation",
    "trojan", "wormable", "trojanized", "backdoor",
    "supply chain attack", "software supply chain", "supply-chain attack",
    "major breach", "data leak", "data leaks", "massive leak",
    "ransom gang", "ransomware", "double extortion", "ransom note",
]

# Promotional content patterns
PROMO_PATTERNS: List[str] = [
    "black friday", "cyber monday", "prime day", "doorbuster",
    "flash sale", "mega sale", "hot sale",
    "limited-time offer", "limited time offer", "time-limited offer",
    "price drop", "price drops", "on sale",
    "lowest price", "lowest-ever price", "cheapest price",
    "save up to", "save $", "save €", "% off",
    "discount code", "discounts on", "coupon code", "voucher code",
    "deal of the day", "deal alert",
    " tv deals", " laptop deals", " monitor deals",
    " ipad deals", " iphone deals", " macbook deals",
    " gaming pc deals", " gaming laptop deals",
    "live-tracking the best", "live tracking the best",
    "i'm live-tracking", "im live-tracking",
]


class Config:
    """Configuration container for easy access and testing."""

    def __init__(
        self,
        *,
        base_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
        vertical: Optional[str] = None,
        opml_path: Optional[str] = None,
        output_path: Optional[str] = None,
        archive_dir: Optional[str] = None,
    ):
        # Default vertical to 'k5' if not provided and present in source/
        if vertical is None and not os.environ.get("K5_VERTICAL") and not os.environ.get("VERTICAL"):
            # __file__ is inside core/code/base/news_fetcher
            from pathlib import Path as _P
            repo_root = _P(__file__).resolve().parents[3]
            if (repo_root / "source" / "k5").exists():
                vertical = "k5"

        path_config: PathConfig = load_path_config(
            start=__file__,
            base_dir=base_dir,
            data_dir=data_dir,
            vertical=vertical,
            opml_path=opml_path,
            output_path=output_path,
            archive_dir=archive_dir,
        )

        self.vertical = path_config.vertical
        self.base_dir = path_config.base_dir
        self.code_dir = path_config.code_dir
        self.data_dir = path_config.data_dir
        self.source_dir = path_config.source_dir
        self.opml_path = path_config.opml_path
        self.output_path = path_config.output_path
        self.archive_dir = path_config.archive_dir
        self.smart_groups_path = None
        if self.vertical:
            candidate = self.code_dir / self.vertical / "smart_groups.py"
            if candidate.exists():
                self.smart_groups_path = candidate
        self.feed_sets = path_config.feed_files or {
            "news": self.opml_path,
        }
        self.feed_types = tuple(self.feed_sets.keys())
        self.days_back = DAYS_BACK
        self.max_workers = MAX_WORKERS
        self.request_timeout = REQUEST_TIMEOUT
        self.curated_keywords = CURATED_KEYWORDS
        self.promo_patterns = PROMO_PATTERNS
        self.summary_allowed_tags = SUMMARY_ALLOWED_TAGS
        self.summary_allowed_attrs = SUMMARY_ALLOWED_ATTRS
        self.summary_allowed_href_prefixes = SUMMARY_ALLOWED_HREF_PREFIXES

        # Categories are now loaded dynamically from OPML
        # Use CategoryMapper for dynamic category resolution

        # Make sure code/<vertical> modules are importable
        code_dir_str = str(self.code_dir)
        if code_dir_str not in sys.path:
            sys.path.insert(0, code_dir_str)
