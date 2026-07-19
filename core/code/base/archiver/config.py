"""Configuration for archive processor."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from path_utils import PathConfig, load_path_config


class Config:
    """Configuration container for archive processor."""

    def __init__(
        self,
        *,
        base_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
        vertical: Optional[str] = None,
        output_path: Optional[str] = None,
        archive_dir: Optional[str] = None,
    ):
        path_config: PathConfig = load_path_config(
            start=__file__,
            base_dir=base_dir,
            data_dir=data_dir,
            vertical=vertical,
            output_path=output_path,
            archive_dir=archive_dir,
        )

        self.base_dir = path_config.base_dir
        self.data_dir = path_config.data_dir
        self.recent_path = path_config.output_path
        self.archive_dir = path_config.archive_dir
        self.feed_files = path_config.feed_files
        self.feed_types = tuple(self.feed_files.keys()) or ("news",)

        self.per_type_archive_dirs: Dict[str, Dict[str, Path]] = {}
        for feed_type in self.feed_types:
            base = self.archive_dir / feed_type
            self.per_type_archive_dirs[feed_type] = {
                "base": base,
                "monthly": base / "monthly",
                "yearly": base / "yearly",
                "daily": base / "daily",
            }

        self.promo_dir = self.archive_dir / "promo"
        self.promo_monthly_dir = self.promo_dir / "monthly"

        # Chunked data paths (for incremental loading)
        self.latest_path = self.data_dir / "latest.json"
        self.index_path = self.data_dir / "index.json"

    def get_monthly_dir(self, feed_type: str) -> Path:
        return self.per_type_archive_dirs.get(feed_type, self.per_type_archive_dirs[self.feed_types[0]])["monthly"]

    def get_yearly_dir(self, feed_type: str) -> Path:
        return self.per_type_archive_dirs.get(feed_type, self.per_type_archive_dirs[self.feed_types[0]])["yearly"]

    def get_daily_dir(self, feed_type: str) -> Path:
        return self.per_type_archive_dirs.get(feed_type, self.per_type_archive_dirs[self.feed_types[0]])["daily"]
