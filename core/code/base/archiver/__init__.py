"""
archiver - Modular news archive management system.

This package provides clean architecture for aggregating news items into
monthly and yearly archives with deduplication and promotional content processing.
"""

from .processor import ArchiveProcessor
from .config import Config

__version__ = "2.0.0"
__all__ = ["ArchiveProcessor", "Config"]
