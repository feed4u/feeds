"""
Trends Analyzer Package

Modern, data science-driven cybersecurity trends analysis.
Provides comprehensive insights, risk scoring, and actionable intelligence.
"""

from .analyzers import (
    AttackPatternAnalyzer,
    AttackSurfaceAnalyzer,
    CVEAnalyzer,
    ThreatActorAnalyzer,
)
from .config import TrendsConfig
from .insights import InsightsGenerator
from .metrics import calculate_risk_score, calculate_velocity, get_risk_level
from .processor import TrendsProcessor

__version__ = "2.1.0"
__all__ = [
    "TrendsConfig",
    "TrendsProcessor",
    "AttackPatternAnalyzer",
    "CVEAnalyzer",
    "ThreatActorAnalyzer",
    "AttackSurfaceAnalyzer",
    "InsightsGenerator",
    "calculate_risk_score",
    "calculate_velocity",
    "get_risk_level",
]
