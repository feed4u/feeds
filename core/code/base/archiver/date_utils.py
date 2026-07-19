"""Date parsing, validation, and bucketing utilities."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def parse_datetime(value: Any) -> Optional[datetime]:
    """
    Convert a date field (ISO string or numeric timestamp) to datetime.

    Args:
        value: ISO string, timestamp (int/float), or None

    Returns:
        Timezone-aware datetime or None
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (ValueError, OSError):
            return None

    if isinstance(value, str):
        try:
            # Handle 'Z' suffix
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            dt = datetime.fromisoformat(value)
            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    return None


def ensure_timestamp(item: Dict[str, Any]) -> float:
    """
    Ensure item has numeric 'published_ts' field (epoch seconds).

    Args:
        item: News item dict

    Returns:
        Timestamp as float (modifies item in-place)
    """
    ts = item.get("published_ts")
    if isinstance(ts, (int, float)):
        return float(ts)

    # Try to parse from published or updated fields
    dt = parse_datetime(item.get("published")) or parse_datetime(
        item.get("updated")
    )

    if dt is None:
        # Fallback to now
        dt = datetime.now(timezone.utc)

    item["published_ts"] = dt.timestamp()
    return item["published_ts"]


def is_valid_date(dt: datetime) -> bool:
    """
    Check if date is valid (not too far in the future).

    Items with dates beyond current year + 1 are invalid.

    Args:
        dt: Datetime to validate

    Returns:
        True if valid
    """
    now = datetime.now(timezone.utc)
    max_year = now.year + 1
    return dt.year <= max_year


def bucket_by_month(
    items: List[Dict[str, Any]]
) -> Dict[Tuple[int, int], List[Dict[str, Any]]]:
    """
    Group items by (year, month) based on published_ts.

    Filters out items with invalid future dates.

    Args:
        items: List of news items

    Returns:
        Dict mapping (year, month) to list of items
    """
    buckets: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}

    for item in items:
        ts = ensure_timestamp(item)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)

        if not is_valid_date(dt):
            title = item.get("title", "No title")[:50]
            print(
                f"[WARN] Skipping item with invalid future date: "
                f"{dt.year}-{dt.month:02d} - {title}"
            )
            continue

        key = (dt.year, dt.month)
        buckets.setdefault(key, []).append(item)

    return buckets


def bucket_by_year(
    items: List[Dict[str, Any]]
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Group items by year based on published_ts.

    Filters out items with invalid future dates.

    Args:
        items: List of news items

    Returns:
        Dict mapping year to list of items
    """
    buckets: Dict[int, List[Dict[str, Any]]] = {}

    for item in items:
        ts = ensure_timestamp(item)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)

        if not is_valid_date(dt):
            continue

        buckets.setdefault(dt.year, []).append(item)

    return buckets


def bucket_by_day(
    items: List[Dict[str, Any]]
) -> Dict[Tuple[int, int, int], List[Dict[str, Any]]]:
    """
    Group items by (year, month, day) based on published_ts.

    Filters out items with invalid future dates.

    Args:
        items: List of news items

    Returns:
        Dict mapping (year, month, day) to list of items
    """
    buckets: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}

    for item in items:
        ts = ensure_timestamp(item)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)

        if not is_valid_date(dt):
            continue

        key = (dt.year, dt.month, dt.day)
        buckets.setdefault(key, []).append(item)

    return buckets
