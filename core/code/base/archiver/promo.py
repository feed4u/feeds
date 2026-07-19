"""Promotional content aggregation and processing."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def normalize_promo_item(
    item: Dict[str, Any], seen_at: datetime
) -> Dict[str, Any]:
    """
    Normalize a promo item to standard format.

    Args:
        item: Raw promo item from promo_filtered_*.json
        seen_at: Datetime when the item was seen

    Returns:
        Normalized promo item with fields:
        - feed_title, xml_url, type_label
        - first_seen, last_seen (ISO8601)
        - total_hits, examples (list, max 10)
    """
    promo_count = _to_int(item.get("promo_count", item.get("count", 0)))

    examples = item.get("examples") or []
    if not isinstance(examples, list):
        examples = [examples]
    examples = [str(e) for e in examples][:10]

    return {
        "feed_title": item.get("feed_title"),
        "xml_url": item.get("xml_url"),
        "type_label": item.get("type_label"),
        "first_seen": seen_at.isoformat(),
        "last_seen": seen_at.isoformat(),
        "total_hits": promo_count,
        "examples": examples,
    }


def merge_promo_entries(
    existing: List[Dict[str, Any]], new_entries: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge promo entries for the same month, aggregating by feed.

    Sums total_hits, merges examples, and adjusts first_seen/last_seen.

    Args:
        existing: Existing promo entries from monthly file
        new_entries: New promo entries to merge

    Returns:
        Merged list of promo entries
    """
    merged: Dict[str, Dict[str, Any]] = {}

    # Copy existing entries
    for item in existing:
        key = _promo_key(item)
        if key:
            merged[key] = dict(item)

    # Merge new entries
    for item in new_entries:
        key = _promo_key(item)
        if not key:
            continue

        if key in merged:
            _merge_promo_item(merged[key], item)
        else:
            # Initialize new entry
            merged[key] = {
                **item,
                "total_hits": _to_int(
                    item.get("total_hits", item.get("promo_count", 0))
                ),
                "examples": item.get("examples") or [],
            }

    return list(merged.values())


def _promo_key(item: Dict[str, Any]) -> Optional[str]:
    """Get unique key for promo item (xml_url or feed_title)."""
    return item.get("xml_url") or item.get("feed_title")


def _to_int(val: Any) -> int:
    """Safely convert value to int."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _merge_promo_item(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """
    Merge source promo item into target.

    Modifies target in-place.
    """
    # Sum total_hits
    target["total_hits"] = _to_int(target.get("total_hits")) + _to_int(
        source.get("total_hits", source.get("promo_count", 0))
    )

    # Merge examples (limit to 10)
    existing_examples = [str(e) for e in (target.get("examples") or [])]
    seen = set(existing_examples)

    source_examples = source.get("examples") or []
    for ex in source_examples:
        ex_str = str(ex)
        if ex_str not in seen:
            existing_examples.append(ex_str)
            seen.add(ex_str)
        if len(existing_examples) >= 10:
            break

    target["examples"] = existing_examples

    # Adjust first_seen / last_seen
    source_first = source.get("first_seen")
    source_last = source.get("last_seen")

    if source_first:
        if not target.get("first_seen") or str(source_first) < str(
            target["first_seen"]
        ):
            target["first_seen"] = source_first

    if source_last:
        if not target.get("last_seen") or str(source_last) > str(
            target["last_seen"]
        ):
            target["last_seen"] = source_last

    # Keep most recent feed metadata
    for field in ("feed_title", "xml_url", "type_label"):
        if source.get(field):
            target[field] = source[field]
