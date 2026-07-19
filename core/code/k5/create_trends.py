#!/usr/bin/env python3
"""
Modern trends analysis with risk scoring, velocity analysis, and actionable insights.

This script uses the trends_analyzer package to generate comprehensive
cybersecurity intelligence from news feeds.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add scripts to path
CURRENT_DIR = Path(__file__).parent
BASE_DIR = CURRENT_DIR.parent / "base"
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(BASE_DIR))

from config.threat_actors import get_threat_actor_names
from path_utils import add_path_cli_arguments, load_path_config
from trends_analyzer import TrendsConfig, TrendsProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate vertical-specific trends data from the latest news JSON."
    )
    add_path_cli_arguments(parser)
    parser.add_argument(
        "--news-path",
        type=Path,
        help="Override news_recent.json path (defaults to resolved data_dir).",
    )
    parser.add_argument(
        "--trends-path",
        type=Path,
        help="Override output trends.json path (defaults to <data_dir>/trends.json).",
    )
    return parser.parse_args()


def load_news_data(path: Path) -> List[Dict[str, Any]]:
    """
    Load news data from JSON file.

    Args:
        path: Path to news_recent.json

    Returns:
        List of news items

    Raises:
        FileNotFoundError: If news file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"News data not found: {path}")

    logger.info(f"Loading news data from {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("items", [])
        logger.info(f"Loaded {len(items)} news items")
        return items

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {str(e)}")
        raise


def save_trends_data(path: Path, data: Dict[str, Any]) -> None:
    """
    Save trends data to JSON file.

    Args:
        path: Output path
        data: Trends data dictionary

    Raises:
        IOError: If file cannot be written
    """
    try:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write with pretty formatting
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Trends data written to {path}")

    except IOError as e:
        logger.error(f"Failed to write {path}: {str(e)}")
        raise


def main() -> int:
    """
    Main execution function.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        args = _parse_args()
        path_config = load_path_config(
            start=__file__,
            base_dir=args.base_dir,
            data_dir=args.data_dir,
            vertical=args.vertical or "k5",
            output_path=args.output_path,
        )
        news_recent_path = args.news_path or path_config.output_path
        trends_output = args.trends_path or (path_config.data_dir / "trends.json")

        # Load configuration
        logger.info("Initializing trends analysis...")
        config = TrendsConfig()
        threat_actor_names = get_threat_actor_names()
        logger.info(f"Loaded {len(threat_actor_names)} threat actor names")

        # Initialize processor
        processor = TrendsProcessor(
            config=config,
            threat_actor_names=threat_actor_names
        )

        # Load news data
        items = load_news_data(news_recent_path)

        if not items:
            logger.warning("No news items found - generating empty report")
            return 1

        # Process trends (30-day analysis)
        logger.info("=" * 60)
        logger.info("Starting trends analysis...")
        logger.info("=" * 60)

        trends_data = processor.process(items, time_range_days=30)

        # Save output
        save_trends_data(trends_output, trends_data)

        # Print summary
        summary = trends_data["summary"]
        insights = trends_data["insights"]

        logger.info("=" * 60)
        logger.info("ANALYSIS COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Risk Score: {summary['risk_score']}/10 ({summary['risk_level'].upper()})")
        logger.info(f"Articles Analyzed: {summary['total_articles']}")
        logger.info(f"Time Range: {summary['time_range_days']} days")
        logger.info(f"Critical Alerts: {summary['critical_alerts']}")
        logger.info(f"Trending Threats: {summary['trending_threats']}")
        logger.info(f"CVEs Identified: {summary['total_cves']} ({summary['exploited_cves']} exploited)")
        logger.info("=" * 60)

        # Show critical actions
        if insights["critical_actions"]:
            logger.info("CRITICAL ACTIONS:")
            for action in insights["critical_actions"]:
                logger.info(f"  • {action}")
            logger.info("=" * 60)

        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        logger.error("Please run 'python scripts/fetch_news.py' first")
        return 1

    except ValueError as e:
        logger.error(f"Invalid data: {str(e)}")
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
