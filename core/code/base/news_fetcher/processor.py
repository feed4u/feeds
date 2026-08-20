"""Feed processing and aggregation engine."""

import json
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import feedparser

from .category_loader import CategoryMapper
from .classifiers import classify_smart_groups
from .config import Config
from .filters import is_curated, is_promotional
from .parsers import clean_html_summary, parse_opml_feeds, parse_published_date
from .smart_groups import get_smart_group_rules


class FeedProcessor:
    """Main feed processing engine."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize feed processor.

        Args:
            config: Configuration object (uses default if None)
        """
        self.config = config or Config()
        socket.setdefaulttimeout(self.config.request_timeout)

        self.items_by_link: Dict[str, dict] = {}
        self.promo_stats: Dict[str, dict] = {}
        self.parse_errors: Dict[str, dict] = {}
        self.connection_errors: Dict[str, dict] = {}
        self.other_errors: Dict[str, dict] = {}
        self.lock = Lock()

        # Initialize category mapper for dynamic category resolution
        self.category_mapper = CategoryMapper(
            self.config.feed_sets, self.config.opml_path
        )
        self.smart_group_rules = get_smart_group_rules(
            self.config.vertical, self.config.smart_groups_path
        )

    def process(self) -> Dict[str, Any]:
        """
        Process all feeds and return aggregated results.

        Returns:
            Dict with items, metadata, and statistics
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self.config.days_back)

        # Load existing items for incremental mode
        self._load_existing_items(cutoff)

        # Process feeds in parallel
        all_feeds: List[Tuple[str, str, str, str]] = []
        for feed_type, path in self.config.feed_sets.items():
            if not path.exists():
                print(f"[WARN] Feed file missing: {path}")
                continue
            for group_title, feed_title, xml_url in parse_opml_feeds(path):
                all_feeds.append((feed_type, group_title, feed_title, xml_url))

        if not all_feeds:
            raise FileNotFoundError("No feed sources found. Ensure news/blog/podcasts XML files exist.")

        total_feeds = len(all_feeds)

        print(
            "[INFO] Using feed sections: "
            + ", ".join(str(path) for path in self.config.feed_sets.values())
        )
        print(f"[INFO] Collecting items from last {self.config.days_back} days")
        print(f"[INFO] Using {self.config.max_workers} parallel workers")
        print(f"[INFO] Found {total_feeds} feeds to process")

        completed_count = 0

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_feed = {
                executor.submit(
                    self._process_single_feed,
                    feed_type,
                    group_title,
                    feed_title,
                    xml_url,
                    cutoff,
                ): (feed_type, group_title, feed_title, xml_url)
                for feed_type, group_title, feed_title, xml_url in all_feeds
            }

            for future in as_completed(future_to_feed):
                feed_type, group_title, feed_title, xml_url = future_to_feed[future]

                with self.lock:
                    completed_count += 1
                    type_slug, type_label = self._normalize_category(group_title)
                    print(
                        f"[{completed_count}/{total_feeds}] Processing: "
                        f"{feed_title} [{type_label}]"
                    )

                try:
                    result = future.result()

                    with self.lock:
                        self._merge_result(result, xml_url, feed_title)

                    # Write error report incrementally
                    if completed_count % 50 == 0:
                        self._write_error_report()

                except Exception as e:
                    with self.lock:
                        print(f"[ERROR] Unexpected error: {feed_title}: {e!r}")
                        self._record_error(
                            "other", group_title, feed_title, xml_url, type(e).__name__, str(e)
                        )

        print(f"\n[INFO] Completed processing {total_feeds} feeds")

        # Final error report
        self._write_error_report()

        # Prepare output
        items_list = sorted(
            self.items_by_link.values(),
            key=lambda x: x["published_ts"] if x["published_ts"] is not None else 0,
            reverse=True,
        )

        return {
            "generated_at": now.isoformat(),
            "days_back": self.config.days_back,
            "total_items": len(items_list),
            "items": items_list,
            "feed_types": list(self.config.feed_types),
        }

    # Cloudflare Pages refuses to deploy any asset over 25 MiB and GitHub
    # rejects blobs over 100 MB, so news_recent.json must stay under both.
    MAX_OUTPUT_BYTES = 22 * 1024 * 1024

    def save_results(self, results: Dict[str, Any]) -> None:
        """Save results to JSON file and write reports."""
        self.config.output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(results, indent=2)
        while len(payload) > self.MAX_OUTPUT_BYTES and results["items"]:
            # Items are newest-first: drop the oldest tail proportionally.
            keep = max(1, int(len(results["items"]) * self.MAX_OUTPUT_BYTES / len(payload)) - 50)
            if keep >= len(results["items"]):
                keep = len(results["items"]) - 1
            print(
                f"[WARN] {self.config.output_path}: over size cap, "
                f"trimming {len(results['items'])} -> {keep} newest items"
            )
            results["items"] = results["items"][:keep]
            results["total_items"] = len(results["items"])
            payload = json.dumps(results, indent=2)
        self.config.output_path.write_text(payload, encoding="utf-8")
        print(f"[INFO] Wrote {results['total_items']} items to {self.config.output_path}")

        self._write_promo_report()
        self._print_error_summary()

    def _load_existing_items(self, cutoff: datetime) -> None:
        """Load existing items for incremental mode."""
        if not self.config.output_path.exists():
            return

        try:
            existing_data = json.loads(
                self.config.output_path.read_text(encoding="utf-8")
            )
            existing_items = existing_data.get("items", [])
            kept_existing = 0

            for item in existing_items:
                link = item.get("link")
                if not link:
                    continue

                pub_ts = item.get("published_ts")
                if pub_ts is not None:
                    try:
                        existing_dt = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
                        if existing_dt < cutoff:
                            continue
                    except Exception:
                        pass

                # Ensure backwards compatibility
                if "curated" not in item:
                    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
                    item["curated"] = is_curated(text, self.config.curated_keywords)

                if "summary_html" not in item:
                    item["summary_html"] = ""

                if "feed_type" not in item:
                    item["feed_type"] = "news"

                self.items_by_link[link] = item
                kept_existing += 1

            if kept_existing:
                print(f"[INFO] Pre-loaded {kept_existing} existing items")

        except Exception as e:
            print(f"[WARN] Could not load existing JSON: {e!r}")

    def _process_single_feed(
        self,
        feed_type: str,
        group_title: str,
        feed_title: str,
        xml_url: str,
        cutoff: datetime,
    ) -> dict:
        """Process a single RSS feed."""
        type_slug, type_label = self._normalize_category(group_title)

        result = {
            "items": [],
            "feed_type": feed_type,
            "promo_stat": {
                "feed_title": feed_title,
                "xml_url": xml_url,
                "type_label": type_label,
                "promo_count": 0,
                "examples": [],
            },
            "parse_error": None,
            "connection_error": None,
            "other_error": None,
        }

        try:
            parsed = feedparser.parse(xml_url)
        except Exception as e:
            self._categorize_exception(result, feed_title, xml_url, type_label, e)
            return result

        # Check for bozo exception
        bozo_info = None
        if getattr(parsed, "bozo", False) and getattr(parsed, "bozo_exception", None):
            bozo_exc = parsed.bozo_exception
            bozo_info = {
                "exc": bozo_exc,
                "type": type(bozo_exc).__name__,
                "msg": str(bozo_exc),
            }

        # Process entries
        for entry in parsed.entries:
            item = self._process_entry(
                entry, feed_title, feed_type, type_slug, type_label, cutoff
            )

            if item is None:
                continue

            if item == "PROMO":
                result["promo_stat"]["promo_count"] += 1
                continue

            result["items"].append(item)

        # Evaluate bozo exceptions after processing
        if bozo_info:
            self._handle_bozo_exception(
                result, bozo_info, feed_title, xml_url, type_label
            )

        return result

    def _process_entry(
        self,
        entry,
        feed_title: str,
        feed_type: str,
        type_slug: str,
        type_label: str,
        cutoff: datetime,
    ) -> Optional[Any]:
        """Process a single feed entry."""
        link = getattr(entry, "link", None)
        title = getattr(entry, "title", "").strip()

        if not link or not title:
            return None

        # Get summary
        content_list = getattr(entry, "content", None)
        if content_list and len(content_list) > 0:
            summary_raw = content_list[0].get("value", "")
        else:
            summary_raw = getattr(entry, "summary", "") or getattr(
                entry, "description", ""
            )

        # Check for promotional content
        promo_text = f"{title} {summary_raw}"
        if is_promotional(promo_text, self.config.promo_patterns):
            return "PROMO"

        # Parse date
        pub_dt = parse_published_date(entry)
        if not pub_dt:
            pub_iso = None
            pub_ts = None
        else:
            if pub_dt < cutoff:
                return None
            pub_iso = pub_dt.isoformat()
            pub_ts = int(pub_dt.timestamp())

        # Clean HTML
        summary, summary_html = clean_html_summary(
            summary_raw,
            self.config.summary_allowed_tags,
            self.config.summary_allowed_attrs,
            self.config.summary_allowed_href_prefixes,
        )

        # Classify (include source title to aid grouping when summaries are empty)
        text = f"{title} {summary} {feed_title}"
        smart_groups = classify_smart_groups(text, self.smart_group_rules)
        curated = is_curated(text, self.config.curated_keywords)

        return {
            "title": title,
            "summary": summary,
            "summary_html": summary_html,
            "link": link,
            "source": feed_title,
            "feed_type": feed_type,
            "type": type_slug,
            "type_label": type_label,
            "published": pub_iso,
            "published_ts": pub_ts,
            "smart_groups": smart_groups,
            "curated": curated,
        }

    def _categorize_exception(
        self, result: dict, feed_title: str, xml_url: str, type_label: str, exc: Exception
    ) -> None:
        """Categorize exception into error types."""
        error_type = type(exc).__name__
        error_msg = str(exc)

        if any(
            err in error_type
            for err in [
                "RemoteDisconnected",
                "ConnectionError",
                "Timeout",
                "URLError",
                "HTTPError",
            ]
        ):
            result["connection_error"] = {
                "feed_title": feed_title,
                "xml_url": xml_url,
                "type_label": type_label,
                "error_type": error_type,
                "error_message": error_msg,
            }
            print(f"[ERROR] Connection error for {feed_title}: {exc!r}")
        else:
            result["other_error"] = {
                "feed_title": feed_title,
                "xml_url": xml_url,
                "type_label": type_label,
                "error_type": error_type,
                "error_message": error_msg,
            }
            print(f"[ERROR] Failed to fetch {feed_title}: {exc!r}")

    def _handle_bozo_exception(
        self, result: dict, bozo_info: dict, feed_title: str, xml_url: str, type_label: str
    ) -> None:
        """Handle bozo exceptions based on whether items were extracted."""
        got_items = len(result["items"]) > 0
        bozo_type = bozo_info["type"]
        bozo_msg = bozo_info["msg"]

        # CharacterEncodingOverride is typically non-fatal - feedparser handles it gracefully
        if bozo_type == "CharacterEncodingOverride":
            if got_items:
                print(f"[WARN] Encoding mismatch in {feed_title} but feed parsed successfully")
            else:
                print(f"[WARN] Encoding mismatch in {feed_title} (no recent items)")
            return

        if got_items:
            print(f"[WARN] Minor XML issue in {feed_title} but feed works: {bozo_type}")
            return

        # No items - categorize error
        if any(
            err in bozo_type
            for err in [
                "URLError",
                "TimeoutError",
                "timeout",
                "ConnectionError",
                "HTTPError",
                "SSLError",
                "gaierror",
            ]
        ):
            result["connection_error"] = {
                "feed_title": feed_title,
                "xml_url": xml_url,
                "type_label": type_label,
                "error_type": bozo_type,
                "error_message": bozo_msg,
            }
        elif any(
            err in bozo_type
            for err in ["SAXParseException", "ParseError", "ExpatError", "XMLSyntaxError"]
        ) or any(
            keyword in bozo_msg.lower() for keyword in ["not well-formed", "invalid token"]
        ):
            result["parse_error"] = {
                "feed_title": feed_title,
                "xml_url": xml_url,
                "type_label": type_label,
                "error_type": bozo_type,
                "error_message": bozo_msg,
            }
        else:
            result["other_error"] = {
                "feed_title": feed_title,
                "xml_url": xml_url,
                "type_label": type_label,
                "error_type": bozo_type,
                "error_message": bozo_msg,
            }

        print(f"[ERROR] Feed error (no items) for {feed_title}: {bozo_type}")

    def _merge_result(self, result: dict, feed_key: str, feed_title: str) -> None:
        """Merge feed processing result into aggregated data."""
        # Store stats
        self.promo_stats[feed_key] = result["promo_stat"]

        # Store errors
        if result["parse_error"]:
            self.parse_errors[feed_key] = result["parse_error"]
        if result["connection_error"]:
            self.connection_errors[feed_key] = result["connection_error"]
        if result["other_error"]:
            self.other_errors[feed_key] = result["other_error"]

        # Merge items
        for item in result["items"]:
            link = item["link"]
            existing = self.items_by_link.get(link)

            if existing is None:
                self.items_by_link[link] = item
            else:
                if (item["published_ts"] or 0) > (existing.get("published_ts") or 0):
                    self.items_by_link[link] = item

    def _record_error(
        self,
        error_type: str,
        group_title: str,
        feed_title: str,
        xml_url: str,
        exc_type: str,
        exc_msg: str,
    ) -> None:
        """Record an error."""
        _, type_label = self._normalize_category(group_title)
        error_dict = {
            "feed_title": feed_title,
            "xml_url": xml_url,
            "type_label": type_label,
            "error_type": exc_type,
            "error_message": exc_msg,
        }

        if error_type == "parse":
            self.parse_errors[xml_url] = error_dict
        elif error_type == "connection":
            self.connection_errors[xml_url] = error_dict
        else:
            self.other_errors[xml_url] = error_dict

    def _normalize_category(self, group_title: str) -> tuple:
        """
        Normalize category group title to slug and label.

        Uses dynamic category mapping from OPML file.
        """
        label = (group_title or "General").strip()
        slug = self.category_mapper.get_slug(label)
        return slug, label

    def _write_error_report(self) -> None:
        """Write error report to disk."""
        total_errors = (
            len(self.parse_errors) + len(self.connection_errors) + len(self.other_errors)
        )

        self.config.archive_dir.mkdir(parents=True, exist_ok=True)
        error_report_latest = self.config.archive_dir / "feed_errors_latest.json"

        error_report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "status": "errors" if total_errors else "ok",
                "total_feeds_with_errors": total_errors,
                "parse_errors_count": len(self.parse_errors),
                "connection_errors_count": len(self.connection_errors),
                "other_errors_count": len(self.other_errors),
            },
            "parse_errors": list(self.parse_errors.values()),
            "connection_errors": list(self.connection_errors.values()),
            "other_errors": list(self.other_errors.values()),
        }

        error_report_latest.write_text(
            json.dumps(error_report, indent=2), encoding="utf-8"
        )

    def _write_promo_report(self) -> None:
        """Write promotional content filter report."""
        total_promo = sum(s["promo_count"] for s in self.promo_stats.values())
        print(f"[INFO] Total promotional items filtered: {total_promo}")

        if total_promo == 0:
            return

        self.config.archive_dir.mkdir(parents=True, exist_ok=True)
        report_latest = self.config.archive_dir / "promo_filtered_latest.json"

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "days_back": self.config.days_back,
            "total_promo_filtered": total_promo,
            "feeds": [
                {
                    "feed_title": s["feed_title"],
                    "xml_url": s["xml_url"],
                    "type_label": s["type_label"],
                    "promo_count": s["promo_count"],
                    "examples": s["examples"][:10],
                }
                for s in self.promo_stats.values()
                if s["promo_count"] > 0
            ],
        }

        report_latest.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[INFO] Updated promo report at {report_latest}")

    def _print_error_summary(self) -> None:
        """Print error summary."""
        total_errors = (
            len(self.parse_errors) + len(self.connection_errors) + len(self.other_errors)
        )

        if total_errors == 0:
            print(f"\n[INFO] No feed errors detected. All feeds processed successfully!")
            return

        print(f"\n[WARN] ====== FEED ERROR SUMMARY ======")
        print(f"[WARN] Total feeds with errors: {total_errors}")
        print(f"[WARN]   - Parse errors: {len(self.parse_errors)}")
        print(f"[WARN]   - Connection errors: {len(self.connection_errors)}")
        print(f"[WARN]   - Other errors: {len(self.other_errors)}")
        print(f"[WARN] See {self.config.archive_dir}/feed_errors_latest.json for details")
