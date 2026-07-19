"""Content filtering for promotional and curated content detection."""

from typing import List


def is_promotional(text: str, patterns: List[str]) -> bool:
    """
    Check if text matches promotional content patterns.

    Args:
        text: Combined title and summary text (lowercase)
        patterns: List of promotional patterns to match

    Returns:
        True if promotional content detected
    """
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in patterns)


def is_curated(text: str, keywords: List[str]) -> bool:
    """
    Check if content matches high-signal curated keywords.

    Args:
        text: Combined title and summary text (lowercase)
        keywords: List of curated keywords to match

    Returns:
        True if content is curated (high-signal)
    """
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)
