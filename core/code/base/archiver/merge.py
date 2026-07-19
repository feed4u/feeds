"""Merge and deduplication logic for news items."""

from typing import Any, Dict, List


def merge_and_dedup(
    existing: List[Dict[str, Any]], new_items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge two lists of news items, deduplicating by 'link'.

    When duplicates exist, keeps the item with the most recent published_ts.

    Args:
        existing: Existing items from archive
        new_items: New items to merge

    Returns:
        Merged and deduplicated list, sorted by published_ts descending
    """
    merged: Dict[str, Dict[str, Any]] = {}

    # Add existing items
    for item in existing:
        link = item.get("link")
        if not link:
            continue
        merged[link] = item

    # Merge new items
    for item in new_items:
        link = item.get("link")
        if not link:
            continue

        if link in merged:
            # Keep the one with the most recent timestamp
            old_ts = merged[link].get("published_ts", 0)
            new_ts = item.get("published_ts", 0)
            if new_ts > old_ts:
                merged[link] = item
        else:
            merged[link] = item

    # Sort by published_ts descending
    result = list(merged.values())
    result.sort(key=_sort_key, reverse=True)
    return result


def _sort_key(item: Dict[str, Any]) -> float:
    """Extract timestamp for sorting."""
    ts = item.get("published_ts")
    if isinstance(ts, (int, float)):
        return float(ts)
    return 0.0
