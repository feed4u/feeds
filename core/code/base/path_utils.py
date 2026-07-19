"""Shared helpers for locating project directories and vertical resources."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Union

PathLike = Union[str, Path]

DEFAULT_FEED_FILENAMES = {
    "news": "news.xml",
    # Support both singular and plural naming across verticals
    "blog": "blog.xml",
    "blogs": "blogs.xml",
    "podcasts": "podcasts.xml",
    "videos": "videos.xml",
    # Additional sections for sovereignty/storage use cases
    "viranomaiset": "viranomaiset.xml",
    "kunnat": "kunnat.xml",
    "laki": "laki.xml",
}


def _to_path(value: Optional[PathLike]) -> Optional[Path]:
    if value is None:
        return None
    if isinstance(value, Path):
        return value.expanduser().resolve()
    return Path(value).expanduser().resolve()


def detect_project_root(start: Optional[PathLike] = None) -> Path:
    """Walk up from the given path until we find the project root.

    This repository uses `core/` (not `code/`) at the root. Detect by
    preferring directories that contain `data/` and `source/`, or `data/`
    and `core/`. Fall back to the parent of the current file.
    """
    current = _to_path(start) or Path(__file__).resolve()
    for candidate in [current, *current.parents]:
        has_data = (candidate / "data").is_dir()
        has_source = (candidate / "source").is_dir()
        has_core = (candidate / "core").is_dir()
        if (has_data and has_source) or (has_data and has_core):
            return candidate
    return current.parent


def _resolve_base_dir(start: Optional[PathLike], override: Optional[PathLike]) -> Path:
    return _to_path(override) or _to_path(os.environ.get("K5_BASE_DIR")) or detect_project_root(start)


@dataclass(frozen=True)
class PathConfig:
    base_dir: Path
    code_dir: Path
    data_dir: Path
    vertical: Optional[str]
    source_dir: Path
    opml_path: Path
    output_path: Path
    archive_dir: Path
    feed_files: Dict[str, Path]


def load_path_config(
    *,
    start: Optional[PathLike] = None,
    base_dir: Optional[PathLike] = None,
    data_dir: Optional[PathLike] = None,
    vertical: Optional[str] = None,
    opml_path: Optional[PathLike] = None,
    source_dir: Optional[PathLike] = None,
    output_filename: str = "news_recent.json",
    output_path: Optional[PathLike] = None,
    archive_dir: Optional[PathLike] = None,
) -> PathConfig:
    """Resolve project paths, honoring CLI/env overrides."""
    base = _resolve_base_dir(start, base_dir)
    code_dir = base / "code"

    env_vertical = os.environ.get("K5_VERTICAL") or os.environ.get("VERTICAL")
    resolved_vertical = vertical or env_vertical

    root_data = _to_path(data_dir) or _to_path(os.environ.get("K5_DATA_DIR")) or (base / "data")
    data_path = root_data
    if resolved_vertical:
        data_path = data_path / resolved_vertical
    data_path = data_path.resolve()

    resolved_source_dir = (
        _to_path(source_dir)
        or _to_path(os.environ.get("K5_SOURCE_DIR"))
        or (base / "source")
    )
    if resolved_vertical:
        vertical_source = resolved_source_dir / resolved_vertical
        if vertical_source.exists():
            resolved_source_dir = vertical_source

    computed_opml = (
        _to_path(opml_path)
        or _to_path(os.environ.get("K5_OPML_PATH"))
        or (resolved_source_dir / "feeds.xml")
    )

    computed_output = (
        _to_path(output_path)
        or _to_path(os.environ.get("K5_OUTPUT_PATH"))
        or (data_path / output_filename)
    )

    computed_archive = (
        _to_path(archive_dir)
        or _to_path(os.environ.get("K5_ARCHIVE_DIR"))
        or (data_path / "archive")
    )

    feed_files = discover_feed_files(resolved_source_dir)

    return PathConfig(
        base_dir=base.resolve(),
        code_dir=code_dir.resolve(),
        data_dir=data_path,
        vertical=resolved_vertical,
        source_dir=resolved_source_dir.resolve(),
        opml_path=computed_opml,
        output_path=computed_output,
        archive_dir=computed_archive,
        feed_files=feed_files,
    )


def add_path_cli_arguments(parser):
    """Attach common path/vertical options to an argparse parser."""
    parser.add_argument(
        "--vertical",
        help="Vertical identifier (e.g., k5, ai-ds). Falls back to VERTICAL env.",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        help="Override auto-detected project root (folder containing code/, data/, source/).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Root directory for generated JSON artifacts (defaults to <base>/data).",
    )
    parser.add_argument(
        "--opml-path",
        type=Path,
        help="Explicit OPML file path; otherwise derived from source directory.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        help="Explicit primary output path (e.g., news_recent.json).",
    )
    parser.add_argument(
        "--archive-dir",
        type=Path,
        help="Explicit archive directory path.",
    )
    return parser


def discover_feed_files(source_dir: Path) -> Dict[str, Path]:
    """Discover available feed section files (news/blogs/podcasts/etc)."""
    feed_files: Dict[str, Path] = {}
    alt_names = {
        "blogs": ["blogs.xml", "blog.xml"],
        "podcasts": ["podcasts.xml", "podcast.xml"],
        "videos": ["videos.xml", "video.xml"],
        "news": ["news.xml"],
        "viranomaiset": ["viranomaiset.xml"],
        "kunnat": ["kunnat.xml"],
        "laki": ["laki.xml"],
    }
    for key, default_name in DEFAULT_FEED_FILENAMES.items():
        candidates = alt_names.get(key, [default_name])
        for name in candidates:
            candidate = source_dir / name
            if candidate.exists():
                feed_files[key] = candidate.resolve()
                break

    if not feed_files:
        fallback = source_dir / "feeds.xml"
        if fallback.exists():
            feed_files["news"] = fallback.resolve()

    return feed_files


__all__ = [
    "PathConfig",
    "add_path_cli_arguments",
    "discover_feed_files",
    "detect_project_root",
    "DEFAULT_FEED_FILENAMES",
    "load_path_config",
]
