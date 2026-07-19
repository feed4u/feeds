#!/usr/bin/env python3
"""
archive_news.py - Modular news archive management.

Aggregates news items from data/news_recent.json into monthly and yearly archives
with deduplication and promotional content processing.
"""

import argparse
import sys
from pathlib import Path

# Ensure local packages are importable when running as a script
sys.path.insert(0, str(Path(__file__).parent))

from archiver import ArchiveProcessor, Config
from path_utils import add_path_cli_arguments


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build archives for the configured vertical's news data."
    )
    add_path_cli_arguments(parser)
    return parser.parse_args()


def main() -> None:
    """Main entry point for archive processing."""
    args = _parse_args()
    try:
        config = Config(
            base_dir=args.base_dir,
            data_dir=args.data_dir,
            vertical=args.vertical,
            output_path=args.output_path,
            archive_dir=args.archive_dir,
        )
        processor = ArchiveProcessor(config)
        stats = processor.process()

        print("\n[INFO] Archive processing completed successfully:")
        print(f"  - Monthly archives updated: {stats['monthly_archives']}")
        print(f"  - Yearly archives updated: {stats['yearly_archives']}")
        print(f"  - Promo files processed: {stats['promo_files']}")

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
