#!/usr/bin/env python3
"""
fetch_news.py - Modern, modular RSS feed aggregation for news verticals.

This script provides a clean, reusable architecture for fetching and processing
news from RSS feeds with classification and filtering.

Usage:
    python core/code/base/fetch_news.py [--vertical security]

Environment Variables:
    DAYS_BACK       - Days of history to retain (default: 30)
    MAX_WORKERS     - Parallel feed download workers (default: 10)
    REQUEST_TIMEOUT - HTTP timeout in seconds (default: 25)
    K5_VERTICAL     - Vertical identifier (e.g., k5, ai-ds)
    K5_BASE_DIR     - Override project root detection
    K5_DATA_DIR     - Override data directory

Example:
    DAYS_BACK=60 MAX_WORKERS=20 python core/code/base/fetch_news.py --vertical k5
"""

import argparse
import sys

from news_fetcher import Config, FeedProcessor
from path_utils import add_path_cli_arguments


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and normalize RSS feeds for the configured vertical."
    )
    add_path_cli_arguments(parser)
    return parser.parse_args()


def main() -> None:
    """Main entry point for news fetching."""
    args = _parse_args()
    try:
        config = Config(
            base_dir=args.base_dir,
            data_dir=args.data_dir,
            vertical=args.vertical,
            opml_path=args.opml_path,
            output_path=args.output_path,
            archive_dir=args.archive_dir,
        )
        processor = FeedProcessor(config)

        # Process all feeds
        results = processor.process()

        # Save results
        processor.save_results(results)

        print("\n[INFO] ✓ News fetching completed successfully")

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
