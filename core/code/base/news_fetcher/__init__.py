"""
news_fetcher - Modular RSS feed aggregation and classification system.

This package provides a clean, reusable architecture for fetching, processing,
and classifying security news from RSS feeds.
"""

from .processor import FeedProcessor
from .config import Config

__version__ = "2.0.0"
__all__ = ["FeedProcessor", "Config"]
