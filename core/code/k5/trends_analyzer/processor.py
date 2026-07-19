"""
Main trends processor orchestrating all analysis components.

This module provides the TrendsProcessor class that coordinates all analysis
and generates the complete trends intelligence report.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .analyzers import (
    AttackPatternAnalyzer,
    AttackSurfaceAnalyzer,
    CVEAnalyzer,
    ThreatActorAnalyzer,
)
from .config import TrendsConfig
from .insights import InsightsGenerator
from .metrics import get_risk_level

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class TrendsProcessor:
    """
    Main orchestrator for trends analysis.

    Coordinates all analyzers and generates comprehensive threat intelligence.
    """

    def __init__(
        self,
        config: Optional[TrendsConfig] = None,
        threat_actor_names: Optional[List[str]] = None
    ):
        """
        Initialize trends processor.

        Args:
            config: TrendsConfig instance (creates default if None)
            threat_actor_names: List of known threat actor names
        """
        self.config = config or TrendsConfig()
        self.threat_actor_names = threat_actor_names or []

        # Initialize analyzers
        self.attack_pattern_analyzer = AttackPatternAnalyzer(self.config)
        self.cve_analyzer = CVEAnalyzer(self.config)
        self.threat_actor_analyzer = ThreatActorAnalyzer(
            self.config,
            self.threat_actor_names
        )
        self.attack_surface_analyzer = AttackSurfaceAnalyzer(self.config)

        # Initialize insights generator
        self.insights_generator = InsightsGenerator()

        logger.info("TrendsProcessor initialized")

    def process(
        self,
        items: List[Dict[str, Any]],
        time_range_days: int = 30
    ) -> Dict[str, Any]:
        """
        Process news items and generate complete trends analysis.

        Args:
            items: List of news items to analyze
            time_range_days: Time range for analysis in days

        Returns:
            Complete trends analysis dictionary ready for JSON output

        Raises:
            ValueError: If items list is empty
            RuntimeError: If analysis fails
        """
        if not items:
            raise ValueError("Items list cannot be empty")

        logger.info(f"Processing {len(items)} items for {time_range_days}-day analysis")

        try:
            # Filter items by time windows
            items_30d = self._filter_by_window(items, 30)
            items_7d = self._filter_by_window(items, 7)
            items_14d = self._filter_by_window(items, 14)
            items_prev_7d = [item for item in items_14d if item not in items_7d]

            logger.info(f"Filtered: {len(items_30d)} (30d), {len(items_7d)} (7d)")

            # Run all analyses
            attack_patterns = self._analyze_attack_patterns(items_30d)
            cve_analysis = self._analyze_cves(items_30d)
            threat_actors = self._analyze_threat_actors(items_30d)
            attack_surface = self._analyze_attack_surface(items_30d)
            comparisons = self._calculate_comparisons(items_7d, items_prev_7d, attack_patterns)

            # Calculate summary statistics
            summary = self._generate_summary(
                items_30d,
                attack_patterns,
                cve_analysis,
                time_range_days
            )

            # Generate insights
            insights = self._generate_insights(
                summary,
                attack_patterns,
                cve_analysis,
                attack_surface,
                threat_actors
            )

            # Build final output
            output = self._build_output(
                summary,
                attack_patterns,
                cve_analysis,
                threat_actors,
                attack_surface,
                comparisons,
                insights
            )

            logger.info(
                f"Analysis complete: Risk {summary['risk_score']}/10 ({summary['risk_level'].upper()})"
            )
            logger.info(
                f"  - {summary['critical_alerts']} critical alerts"
            )
            logger.info(
                f"  - {summary['trending_threats']} trending threats"
            )
            logger.info(
                f"  - {len(attack_surface)} attack surfaces identified"
            )

            return output

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise RuntimeError(f"Failed to process trends: {str(e)}") from e

    def _filter_by_window(self, items: List[Dict], days: int) -> List[Dict]:
        """Filter items within time window."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_ts = cutoff.timestamp()

        filtered = []
        for item in items:
            pub_ts = item.get("published_ts")
            # Skip items with None or invalid timestamps
            if pub_ts is not None and pub_ts >= cutoff_ts:
                filtered.append(item)

        return filtered

    def _analyze_attack_patterns(self, items: List[Dict]) -> List[Dict]:
        """Analyze attack patterns with velocity."""
        logger.info("Analyzing attack patterns...")

        # Use earlier period for velocity comparison
        earlier_items = self._filter_by_window(items, 60)[:len(items) // 2]

        try:
            patterns = self.attack_pattern_analyzer.analyze(
                items,
                comparison_items=earlier_items
            )
            logger.info(f"  Found {len(patterns)} active attack patterns")
            return patterns
        except Exception as e:
            logger.error(f"  Attack pattern analysis failed: {str(e)}")
            return []

    def _analyze_cves(self, items: List[Dict]) -> Dict[str, Any]:
        """Analyze CVEs with severity and risk scoring."""
        logger.info("Analyzing CVEs...")

        try:
            analysis = self.cve_analyzer.analyze(items)
            logger.info(
                f"  Found {analysis['total_unique']} unique CVEs, "
                f"{analysis['total_exploited']} exploited"
            )
            return analysis
        except Exception as e:
            logger.error(f"  CVE analysis failed: {str(e)}")
            return {
                "top_cves": [],
                "by_severity": {"critical": {"count": 0, "exploited": 0}, "high": {"count": 0, "exploited": 0}},
                "total_unique": 0,
                "total_exploited": 0
            }

    def _analyze_threat_actors(self, items: List[Dict]) -> Dict[str, Any]:
        """Analyze threat actor activity."""
        logger.info("Analyzing threat actors...")

        try:
            analysis = self.threat_actor_analyzer.analyze(items)
            logger.info(
                f"  Tracked {analysis['total_unique']} unique actors, "
                f"{len(analysis['timeline'])} days of activity"
            )
            return analysis
        except Exception as e:
            logger.error(f"  Threat actor analysis failed: {str(e)}")
            return {
                "most_active": [],
                "total_unique": 0,
                "timeline": []
            }

    def _analyze_attack_surface(self, items: List[Dict]) -> Dict[str, Any]:
        """Analyze attack surfaces."""
        logger.info("Analyzing attack surfaces...")

        try:
            analysis = self.attack_surface_analyzer.analyze(items)
            logger.info(f"  Identified {len(analysis)} attack surfaces")
            return analysis
        except Exception as e:
            logger.error(f"  Attack surface analysis failed: {str(e)}")
            return {}

    def _calculate_comparisons(
        self,
        items_current: List[Dict],
        items_previous: List[Dict],
        attack_patterns: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate week-over-week comparisons."""
        logger.info("Calculating comparisons...")

        try:
            current_volume = len(items_current)
            previous_volume = len(items_previous)
            volume_change = (
                ((current_volume - previous_volume) / max(previous_volume, 1)) * 100
            )

            current_critical = sum(
                1 for p in attack_patterns if p["severity"] == "critical"
            )

            comparisons = {
                "week_over_week": {
                    "total_volume": {
                        "current": current_volume,
                        "previous": previous_volume,
                        "change_percent": round(volume_change, 1),
                        "change_label": "increase" if volume_change > 0 else "decrease"
                    },
                    "critical_threats": {
                        "current": current_critical,
                        "change_label": "threats detected"
                    }
                }
            }

            logger.info(
                f"  Volume: {current_volume} ({volume_change:+.1f}%), "
                f"Critical: {current_critical}"
            )

            return comparisons

        except Exception as e:
            logger.error(f"  Comparison calculation failed: {str(e)}")
            return {
                "week_over_week": {
                    "total_volume": {
                        "current": len(items_current),
                        "previous": len(items_previous),
                        "change_percent": 0,
                        "change_label": "stable"
                    },
                    "critical_threats": {
                        "current": 0,
                        "change_label": "unknown"
                    }
                }
            }

    def _generate_summary(
        self,
        items: List[Dict],
        attack_patterns: List[Dict],
        cve_analysis: Dict[str, Any],
        time_range_days: int
    ) -> Dict[str, Any]:
        """Generate executive summary."""
        logger.info("Generating summary statistics...")

        # Calculate overall risk score
        avg_attack_risk = (
            sum(p["risk_score"] for p in attack_patterns[:5]) /
            max(1, len(attack_patterns[:5]))
        )
        cve_risk = (
            (cve_analysis["total_exploited"] / max(1, cve_analysis["total_unique"])) * 10
        )
        overall_risk = (avg_attack_risk + cve_risk) / 2

        summary = {
            "total_articles": len(items),
            "time_range_days": time_range_days,
            "critical_alerts": len([
                p for p in attack_patterns if p["severity"] == "critical"
            ]),
            "trending_threats": len([
                p for p in attack_patterns if p["velocity"] in ["surging", "rising"]
            ]),
            "risk_score": round(overall_risk, 1),
            "risk_level": get_risk_level(overall_risk),
            "total_cves": cve_analysis["total_unique"],
            "exploited_cves": cve_analysis["total_exploited"]
        }

        return summary

    def _generate_insights(
        self,
        summary: Dict[str, Any],
        attack_patterns: List[Dict],
        cve_analysis: Dict[str, Any],
        attack_surface: Dict[str, Any],
        threat_actors: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate actionable insights."""
        logger.info("Generating actionable insights...")

        try:
            insights = self.insights_generator.generate(
                summary,
                attack_patterns,
                cve_analysis,
                attack_surface,
                threat_actors
            )

            logger.info(
                f"  Generated {len(insights['critical_actions'])} critical actions, "
                f"{len(insights['watch_list'])} watch items"
            )

            return insights

        except Exception as e:
            logger.error(f"  Insight generation failed: {str(e)}")
            return {
                "critical_actions": [],
                "watch_list": [],
                "trending_up": [],
                "trending_down": []
            }

    def _build_output(
        self,
        summary: Dict[str, Any],
        attack_patterns: List[Dict],
        cve_analysis: Dict[str, Any],
        threat_actors: Dict[str, Any],
        attack_surface: Dict[str, Any],
        comparisons: Dict[str, Any],
        insights: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Build final output structure."""
        now = datetime.now(timezone.utc)

        return {
            "generated_at": now.isoformat(),
            "version": "2.1",
            "summary": summary,
            "threat_intelligence": {
                "attack_patterns": attack_patterns,
            },
            "cve_analysis": cve_analysis,
            "threat_actors": threat_actors,
            "attack_surface": attack_surface,
            "comparisons": comparisons,
            "insights": insights,
            # Legacy compatibility
            "windows": list(self.config.windows.keys()),
        }
