"""Main archive processing engine."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import Config
from .date_utils import bucket_by_day, bucket_by_month, bucket_by_year
from .io_utils import load_json_any, load_json_list, save_json_list
from .merge import merge_and_dedup
from .promo import merge_promo_entries, normalize_promo_item


class ArchiveProcessor:
    """Main archive processing engine."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize archive processor.

        Args:
            config: Configuration object (uses default if None)
        """
        self.config = config or Config()

    def process(self) -> Dict[str, Any]:
        """
        Process recent news items into archives.

        Returns:
            Dict with statistics about processed archives
        """
        if not self.config.recent_path.exists():
            raise FileNotFoundError(
                f"Recent file not found: {self.config.recent_path}"
            )

        # Load recent items
        recent_items = load_json_list(
            self.config.recent_path, root_key="items"
        )
        print(
            f"[INFO] Loaded {len(recent_items)} recent items from "
            f"{self.config.recent_path}"
        )

        if not recent_items:
            print("[INFO] No recent items to archive.")
            return {"monthly_archives": 0, "yearly_archives": 0, "promo_files": 0}

        items_by_type = self._group_items_by_feed_type(recent_items)

        monthly_count = 0
        yearly_count = 0

        for feed_type, items in items_by_type.items():
            if not items:
                continue
            monthly_buckets = bucket_by_month(items)
            yearly_buckets = bucket_by_year(items)

            monthly_count += self._process_monthly_archives(
                monthly_buckets, self.config.get_monthly_dir(feed_type), feed_type
            )
            yearly_count += self._process_yearly_archives(
                yearly_buckets, self.config.get_yearly_dir(feed_type), feed_type
            )

        # Process promotional content
        promo_count = self._process_promo_files()

        # Process daily archives for chunked loading
        daily_count = 0
        for feed_type, items in items_by_type.items():
            if not items:
                continue
            daily_buckets = bucket_by_day(items)
            daily_count += self._process_daily_archives(
                daily_buckets, self.config.get_daily_dir(feed_type), feed_type
            )

        # Generate latest.json (24h rolling window)
        self._process_latest_24h(recent_items)

        # Generate index.json (manifest of available chunks)
        self._generate_index()

        return {
            "monthly_archives": monthly_count,
            "yearly_archives": yearly_count,
            "daily_archives": daily_count,
            "promo_files": promo_count,
        }

    def _group_items_by_feed_type(
        self, items: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {ft: [] for ft in self.config.feed_types}
        default_type = self.config.feed_types[0]

        for item in items:
            feed_type = (item.get("feed_type") or default_type).lower()
            grouped.setdefault(feed_type, []).append(item)

        return grouped

    def _process_monthly_archives(
        self,
        buckets: Dict[Tuple[int, int], List[Dict[str, Any]]],
        base_dir: Path,
        feed_type: str,
    ) -> int:
        """Process monthly archive files."""
        count = 0

        for (year, month), items in sorted(buckets.items()):
            year_str = f"{year}"
            month_str = f"{month:02d}"

            month_dir = base_dir / year_str
            month_path = month_dir / f"{year_str}-{month_str}.json"
            month_dir.mkdir(parents=True, exist_ok=True)

            existing = load_json_list(month_path)
            merged = merge_and_dedup(existing, items)
            save_json_list(month_path, merged)

            print(
                f"[INFO] [{feed_type}] Monthly file updated: {month_path} "
                f"(+{len(items)} items, total {len(merged)})"
            )
            count += 1

        return count

    def _process_yearly_archives(
        self,
        buckets: Dict[int, List[Dict[str, Any]]],
        base_dir: Path,
        feed_type: str,
    ) -> int:
        """Process yearly archive files."""
        count = 0

        for year, items in sorted(buckets.items()):
            year_str = f"{year}"
            base_dir.mkdir(parents=True, exist_ok=True)
            year_path = base_dir / f"{year_str}.json"

            existing = load_json_list(year_path)
            merged = merge_and_dedup(existing, items)
            save_json_list(year_path, merged)

            print(
                f"[INFO] [{feed_type}] Yearly file updated: {year_path} "
                f"(+{len(items)} items, total {len(merged)})"
            )
            count += 1

        return count

    def _process_promo_files(self) -> int:
        """
        Process promo_filtered_* files into monthly aggregates.

        Returns:
            Number of promo files processed
        """
        promo_files = sorted(
            self.config.archive_dir.glob("promo_filtered_*.json")
        )

        if not promo_files:
            print("[INFO] No promo_filtered_* files to process.")
            return 0

        monthly_new: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}

        # Load and bucket promo files by month
        for path in promo_files:
            try:
                raw = load_json_any(path)
            except Exception as e:
                print(f"[WARN] Failed to read {path}: {e}")
                continue

            if raw is None:
                continue

            # Get file modification time for bucketing
            mtime = path.stat().st_mtime
            seen_at = datetime.fromtimestamp(mtime, tz=timezone.utc)
            key = (seen_at.year, seen_at.month)

            # Extract feed list
            feeds = self._extract_promo_feeds(raw)
            if not feeds:
                continue

            # Normalize promo items
            normalized = [
                normalize_promo_item(f, seen_at)
                for f in feeds
                if isinstance(f, dict)
            ]

            monthly_new.setdefault(key, []).extend(normalized)

        # Write monthly promo files
        for (year, month), new_entries in sorted(monthly_new.items()):
            self._write_monthly_promo(year, month, new_entries)

        # Clean up processed files
        self._cleanup_promo_files(promo_files)

        return len(promo_files)

    def _extract_promo_feeds(self, raw: Any) -> List[Dict[str, Any]]:
        """Extract feeds list from raw promo data."""
        if isinstance(raw, dict):
            return raw.get("feeds") or []
        elif isinstance(raw, list):
            return raw
        return []

    def _write_monthly_promo(
        self, year: int, month: int, new_entries: List[Dict[str, Any]]
    ) -> None:
        """Write monthly promotional content file."""
        year_str = f"{year}"
        month_str = f"{month:02d}"

        promo_month_dir = self.config.promo_monthly_dir / year_str
        promo_month_path = (
            promo_month_dir / f"promo_{year_str}-{month_str}.json"
        )

        existing = load_json_list(promo_month_path)
        merged = merge_promo_entries(existing, new_entries)
        save_json_list(promo_month_path, merged)

        print(
            f"[INFO] Monthly promo file updated: {promo_month_path} "
            f"(+{len(new_entries)} feeds, total {len(merged)} feeds)"
        )

    def _cleanup_promo_files(self, promo_files: List[Path]) -> None:
        """Delete processed promo files."""
        for path in promo_files:
            try:
                path.unlink()
                print(f"[INFO] File processed and removed: {path}")
            except OSError as e:
                print(f"[WARN] Could not delete {path}: {e}")

    def _process_daily_archives(
        self,
        buckets: Dict[Tuple[int, int, int], List[Dict[str, Any]]],
        base_dir: Path,
        feed_type: str,
    ) -> int:
        """Process daily archive files for incremental loading."""
        count = 0
        base_dir.mkdir(parents=True, exist_ok=True)

        # Sort buckets by date (newest first) to determine next_chunk links
        sorted_dates = sorted(buckets.keys(), reverse=True)

        for i, (year, month, day) in enumerate(sorted_dates):
            items = buckets[(year, month, day)]
            date_str = f"{year}-{month:02d}-{day:02d}"
            daily_path = base_dir / f"{date_str}.json"

            # Determine next chunk (older day)
            next_chunk = None
            if i + 1 < len(sorted_dates):
                next_year, next_month, next_day = sorted_dates[i + 1]
                next_date_str = f"{next_year}-{next_month:02d}-{next_day:02d}"
                next_chunk = f"archive/{feed_type}/daily/{next_date_str}.json"

            # Load existing and merge
            existing = load_json_list(daily_path)
            merged = merge_and_dedup(existing, items)

            # Sort by timestamp descending
            merged.sort(key=lambda x: x.get("published_ts", 0), reverse=True)

            # Save with metadata wrapper
            output = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "date": date_str,
                "total_items": len(merged),
                "next_chunk": next_chunk,
                "items": merged,
            }
            daily_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

            print(
                f"[INFO] [{feed_type}] Daily file updated: {daily_path} "
                f"(+{len(items)} items, total {len(merged)})"
            )
            count += 1

        return count

    def _process_latest_24h(self, items: List[Dict[str, Any]]) -> None:
        """Generate latest.json with items from last 24 hours."""
        now = datetime.now(timezone.utc)
        cutoff_24h = now - timedelta(hours=24)

        # Filter items from last 24h
        items_24h = []
        for item in items:
            ts = item.get("published_ts")
            if ts is None:
                continue
            try:
                pub_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                if pub_dt >= cutoff_24h:
                    items_24h.append(item)
            except Exception:
                continue

        # Sort by timestamp descending
        items_24h.sort(key=lambda x: x.get("published_ts", 0), reverse=True)

        # Determine next chunk (most recent daily file that's older than 24h)
        next_chunk = None
        yesterday = now - timedelta(days=1)
        # Find the first daily file for any feed type
        for feed_type in self.config.feed_types:
            daily_dir = self.config.get_daily_dir(feed_type)
            if daily_dir.exists():
                daily_files = sorted(daily_dir.glob("*.json"), reverse=True)
                for daily_file in daily_files:
                    date_str = daily_file.stem
                    next_chunk = f"archive/{feed_type}/daily/{date_str}.json"
                    break
                if next_chunk:
                    break

        # Create metadata wrapper
        output = {
            "generated_at": now.isoformat(),
            "time_window_hours": 24,
            "total_items": len(items_24h),
            "next_chunk": next_chunk,
            "items": items_24h,
        }

        # Write latest.json
        self.config.latest_path.write_text(
            json.dumps(output, indent=2), encoding="utf-8"
        )
        print(
            f"[INFO] Generated {self.config.latest_path} with "
            f"{len(items_24h)} items from last 24h"
        )

    def _generate_index(self) -> None:
        """Generate index.json listing all available data chunks."""
        now = datetime.now(timezone.utc)

        # Get latest.json info
        latest_info = None
        if self.config.latest_path.exists():
            try:
                data = json.loads(self.config.latest_path.read_text(encoding="utf-8"))
                latest_info = {
                    "file": "latest.json",
                    "item_count": data.get("total_items", 0),
                    "time_window_hours": data.get("time_window_hours", 24),
                }
            except Exception as e:
                print(f"[WARN] Could not read latest.json: {e}")

        # Get daily files info (combine all feed types)
        daily_files = []
        for feed_type in self.config.feed_types:
            daily_dir = self.config.get_daily_dir(feed_type)
            if daily_dir.exists():
                for path in sorted(daily_dir.glob("*.json"), reverse=True):
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                        daily_files.append({
                            "file": f"archive/{feed_type}/daily/{path.name}",
                            "date": path.stem,
                            "item_count": data.get("total_items", len(data.get("items", []))),
                        })
                    except Exception as e:
                        print(f"[WARN] Could not read {path}: {e}")

        # Sort daily files by date descending
        daily_files.sort(key=lambda x: x["date"], reverse=True)

        # Get monthly files info
        monthly_files = []
        for feed_type in self.config.feed_types:
            monthly_dir = self.config.get_monthly_dir(feed_type)
            if monthly_dir.exists():
                for year_dir in sorted(monthly_dir.iterdir(), reverse=True):
                    if not year_dir.is_dir():
                        continue
                    for path in sorted(year_dir.glob("*.json"), reverse=True):
                        try:
                            items = load_json_list(path)
                            monthly_files.append({
                                "file": f"archive/{feed_type}/monthly/{year_dir.name}/{path.name}",
                                "date": path.stem,
                                "item_count": len(items),
                            })
                        except Exception as e:
                            print(f"[WARN] Could not read {path}: {e}")

        # Build index
        index = {
            "generated_at": now.isoformat(),
            "latest": latest_info,
            "daily": daily_files,
            "monthly": monthly_files,
        }

        # Write index.json
        self.config.index_path.write_text(
            json.dumps(index, indent=2), encoding="utf-8"
        )
        print(
            f"[INFO] Generated {self.config.index_path} with "
            f"{len(daily_files)} daily files, {len(monthly_files)} monthly files"
        )
