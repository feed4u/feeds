"""Smart group classification based on keyword matching."""

from typing import List, Sequence, Tuple

from .smart_groups import get_smart_group_rules


def classify_smart_groups(
    text: str, rules: Sequence[Tuple[str, Sequence[str]]] | None = None
) -> List[str]:
    """
    Classify content into smart groups based on keyword matching.

    Args:
        text: Combined title and summary text (lowercase)
        rules: Optional pre-loaded list of (group, keywords) tuples

    Returns:
        List of matching smart group names (deduplicated, preserving order)
    """
    text_lower = text.lower()
    groups: List[str] = []
    seen: set = set()

    smart_group_rules = rules or get_smart_group_rules()

    for group_name, keywords in smart_group_rules:
        if group_name in seen:
            continue

        for keyword in keywords:
            if keyword.lower() in text_lower:
                groups.append(group_name)
                seen.add(group_name)
                break

    return groups
