"""
Metrics calculation for trends analysis including velocity, severity scoring, and risk indicators.
"""

import re
from typing import Dict, List, Optional, Tuple
from collections import Counter


def calculate_velocity(current: int, previous: int) -> Tuple[str, float]:
    """
    Calculate velocity (trend direction) and percent change.

    Returns:
        Tuple of (velocity_label, change_percent)
        velocity_label: "surging", "rising", "stable", "declining"
    """
    if previous == 0:
        if current > 0:
            return ("surging", 100.0)
        return ("stable", 0.0)

    change_ratio = current / previous
    change_percent = ((current - previous) / previous) * 100

    if change_ratio >= 2.0:
        return ("surging", change_percent)
    elif change_ratio >= 1.5:
        return ("rising", change_percent)
    elif change_ratio >= 0.8:
        return ("stable", change_percent)
    else:
        return ("declining", change_percent)


def calculate_risk_score(
    base_severity: float,
    is_exploited: bool = False,
    patch_available: bool = True,
    mentions: int = 1,
    velocity: str = "stable"
) -> float:
    """
    Calculate comprehensive risk score (0-10 scale).

    Factors:
    - Base severity (1-4): Critical=4, High=3, Medium=2, Low=1
    - Active exploitation: +3.0
    - No patch available: +2.0
    - High mention count: +0-1.5
    - Velocity: surging=+1.0, rising=+0.5

    Returns:
        Risk score between 0.0 and 10.0
    """
    score = base_severity * 2.0  # Base: 2-8

    # Exploitation multiplier
    if is_exploited:
        score += 3.0

    # Patch availability
    if not patch_available:
        score += 2.0

    # Mentions (logarithmic scaling)
    if mentions > 10:
        score += min(1.5, (mentions - 10) / 20.0)
    elif mentions > 5:
        score += 0.5

    # Velocity factor
    if velocity == "surging":
        score += 1.0
    elif velocity == "rising":
        score += 0.5

    return min(10.0, max(0.0, score))


def get_risk_level(score: float) -> str:
    """
    Convert numeric risk score to risk level label.

    Returns:
        "critical", "elevated", "moderate", or "low"
    """
    if score >= 8.0:
        return "critical"
    elif score >= 6.0:
        return "elevated"
    elif score >= 4.0:
        return "moderate"
    else:
        return "low"


def analyze_text_for_risks(text: str, risk_indicators: List[Dict]) -> List[Dict[str, any]]:
    """
    Analyze text content for risk indicator patterns.

    Args:
        text: Text to analyze (lowercase)
        risk_indicators: List of risk indicator patterns from config

    Returns:
        List of matched risk indicators with weights
    """
    text_lower = text.lower()
    matched_risks = []

    for indicator in risk_indicators:
        pattern = indicator["pattern"]
        if re.search(pattern, text_lower, re.IGNORECASE):
            matched_risks.append({
                "pattern": indicator["description"],
                "weight": indicator["weight"],
            })

    return matched_risks


def calculate_severity_distribution(cve_counts: Dict[str, int]) -> Dict[str, any]:
    """
    Calculate severity distribution statistics.

    Returns:
        Dict with counts, percentages, and insights
    """
    total = sum(cve_counts.values())
    if total == 0:
        return {
            "critical": {"count": 0, "percent": 0},
            "high": {"count": 0, "percent": 0},
            "medium": {"count": 0, "percent": 0},
            "low": {"count": 0, "percent": 0},
            "total": 0
        }

    distribution = {}
    for severity in ["critical", "high", "medium", "low"]:
        count = cve_counts.get(severity, 0)
        distribution[severity] = {
            "count": count,
            "percent": round((count / total) * 100, 1)
        }

    distribution["total"] = total
    return distribution


def extract_top_n(counter: Counter, n: int = 10, min_count: int = 1) -> List[Tuple[str, int]]:
    """
    Extract top N items from Counter with minimum count threshold.

    Returns:
        List of (item, count) tuples sorted by count descending
    """
    return [(item, count) for item, count in counter.most_common(n) if count >= min_count]


def calculate_trend_strength(counts_over_time: List[int]) -> str:
    """
    Calculate trend strength based on time series data.

    Returns:
        "strong_uptrend", "moderate_uptrend", "stable", "moderate_downtrend", "strong_downtrend"
    """
    if len(counts_over_time) < 2:
        return "stable"

    # Simple linear regression
    n = len(counts_over_time)
    x_mean = (n - 1) / 2
    y_mean = sum(counts_over_time) / n

    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(counts_over_time))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return "stable"

    slope = numerator / denominator

    # Normalize by mean to get relative trend
    relative_slope = (slope / (y_mean + 1)) * 100  # +1 to avoid division by zero

    if relative_slope > 20:
        return "strong_uptrend"
    elif relative_slope > 5:
        return "moderate_uptrend"
    elif relative_slope < -20:
        return "strong_downtrend"
    elif relative_slope < -5:
        return "moderate_downtrend"
    else:
        return "stable"


def normalize_percentage(value: float, decimals: int = 1) -> float:
    """Normalize percentage for display"""
    return round(value, decimals)


def format_change_percent(change: float) -> str:
    """Format change percentage with sign"""
    if change > 0:
        return f"+{change:.1f}%"
    return f"{change:.1f}%"
