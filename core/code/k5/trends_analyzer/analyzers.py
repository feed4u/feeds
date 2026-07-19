"""
Specialized analyzers for cybersecurity trends analysis.

This module contains analyzer classes for different aspects of threat intelligence:
- AttackPatternAnalyzer: Analyzes attack patterns with velocity
- CVEAnalyzer: Analyzes CVEs with severity and risk scoring
- ThreatActorAnalyzer: Analyzes threat actor activity and timeline
- AttackSurfaceAnalyzer: Analyzes attack surfaces with risk weighting
"""

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .config import TrendsConfig
from .metrics import calculate_velocity, calculate_risk_score


class BaseAnalyzer:
    """Base class for all analyzers with common functionality."""

    def __init__(self, config: TrendsConfig):
        """
        Initialize analyzer with configuration.

        Args:
            config: TrendsConfig instance with patterns and settings
        """
        self.config = config

    def _extract_text(self, item: Dict[str, Any]) -> str:
        """Extract searchable text from news item."""
        return f"{item.get('title', '')} {item.get('summary', '')}".lower()

    def _filter_by_window(self, items: List[Dict], days: int) -> List[Dict]:
        """Filter items within time window."""
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_ts = cutoff.timestamp()

        return [
            item for item in items
            if item.get("published_ts", 0) >= cutoff_ts
        ]


class AttackPatternAnalyzer(BaseAnalyzer):
    """Analyzes attack patterns with velocity and risk scoring."""

    def analyze(self, items: List[Dict], comparison_items: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Analyze attack patterns from news items.

        Args:
            items: Current period news items
            comparison_items: Previous period items for velocity calculation

        Returns:
            List of attack pattern analysis results sorted by risk score
        """
        pattern_counts = {pattern: 0 for pattern in self.config.attack_patterns.keys()}
        pattern_items = {pattern: [] for pattern in self.config.attack_patterns.keys()}

        # Count current period patterns
        for item in items:
            text = self._extract_text(item)
            for pattern_key, pattern_config in self.config.attack_patterns.items():
                if self._pattern_matches(text, pattern_config["keywords"]):
                    pattern_counts[pattern_key] += 1
                    pattern_items[pattern_key].append(item)

        # Count comparison period patterns for velocity
        earlier_counts = {}
        if comparison_items:
            earlier_counts = self._count_patterns(comparison_items)

        # Build results
        results = []
        for pattern_key, pattern_config in self.config.attack_patterns.items():
            current_count = pattern_counts[pattern_key]

            if current_count == 0:
                continue

            previous_count = earlier_counts.get(pattern_key, 0)
            velocity, change_pct = calculate_velocity(current_count, previous_count)

            # Calculate risk score
            severity_score = self.config.get_severity_score(pattern_config["severity"])
            risk_score = calculate_risk_score(
                base_severity=severity_score,
                mentions=current_count,
                velocity=velocity
            )

            results.append({
                "name": pattern_config["label"],
                "key": pattern_key,
                "severity": pattern_config["severity"],
                "count": current_count,
                "velocity": velocity,
                "change_percent": round(change_pct, 1),
                "risk_score": round(risk_score, 2),
                "mitre_techniques": pattern_config.get("mitre", []),
                "description": pattern_config["description"]
            })

        # Sort by risk score descending
        results.sort(key=lambda x: x["risk_score"], reverse=True)
        return results

    def _pattern_matches(self, text: str, keywords: List[str]) -> bool:
        """Check if any keyword matches in text."""
        return any(keyword.lower() in text for keyword in keywords)

    def _count_patterns(self, items: List[Dict]) -> Dict[str, int]:
        """Count pattern occurrences in items."""
        counts = {pattern: 0 for pattern in self.config.attack_patterns.keys()}

        for item in items:
            text = self._extract_text(item)
            for pattern_key, pattern_config in self.config.attack_patterns.items():
                if self._pattern_matches(text, pattern_config["keywords"]):
                    counts[pattern_key] += 1
                    break

        return counts


class CVEAnalyzer(BaseAnalyzer):
    """Analyzes CVEs with severity, exploitation status, and risk scoring."""

    CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,}")

    def analyze(self, items: List[Dict]) -> Dict[str, Any]:
        """
        Analyze CVEs from news items.

        Args:
            items: News items to analyze

        Returns:
            Dict with CVE analysis including top CVEs, severity distribution
        """
        cve_details = {}

        # Extract and analyze CVEs
        for item in items:
            text = f"{item.get('title', '')} {item.get('summary', '')}"
            text_upper = text.upper()
            text_lower = text.lower()

            cves = self.CVE_PATTERN.findall(text_upper)

            for cve in cves:
                if cve not in cve_details:
                    cve_details[cve] = {
                        "cve_id": cve,
                        "mentions": 0,
                        "is_exploited": False,
                        "is_critical": False,
                        "vendors": set(),
                    }

                cve_details[cve]["mentions"] += 1

                # Check for exploitation indicators
                if self._is_exploited(text_lower):
                    cve_details[cve]["is_exploited"] = True

                # Check for critical severity
                if self._is_critical(text_lower):
                    cve_details[cve]["is_critical"] = True

                # Extract affected vendors
                cve_details[cve]["vendors"].update(
                    self._extract_vendors(text_lower)
                )

        # Calculate risk scores and build CVE list
        cve_list = self._build_cve_list(cve_details)

        # Calculate severity distribution
        severity_counts = Counter(cve["severity"] for cve in cve_list)

        return {
            "top_cves": cve_list[:20],
            "by_severity": {
                "critical": {
                    "count": severity_counts.get("critical", 0),
                    "exploited": sum(1 for c in cve_list if c["severity"] == "critical" and c["exploited"])
                },
                "high": {
                    "count": severity_counts.get("high", 0),
                    "exploited": sum(1 for c in cve_list if c["severity"] == "high" and c["exploited"])
                },
            },
            "total_unique": len(cve_list),
            "total_exploited": sum(1 for c in cve_list if c["exploited"])
        }

    def _is_exploited(self, text: str) -> bool:
        """Check if CVE is being exploited."""
        exploitation_keywords = [
            "exploited", "exploitation", "under attack",
            "actively exploited", "in the wild"
        ]
        return any(keyword in text for keyword in exploitation_keywords)

    def _is_critical(self, text: str) -> bool:
        """Check if CVE has critical severity."""
        critical_keywords = [
            "critical", "severity: critical",
            "cvss 9", "cvss 10", "cvss: 9", "cvss: 10"
        ]
        return any(keyword in text for keyword in critical_keywords)

    def _extract_vendors(self, text: str) -> set:
        """Extract affected vendor names from text."""
        vendors = set()
        for vendor, keywords in self.config.vendor_keywords.items():
            if any(keyword.lower() in text for keyword in keywords):
                vendors.add(vendor)
        return vendors

    def _build_cve_list(self, cve_details: Dict) -> List[Dict]:
        """Build and sort CVE list with risk scores."""
        cve_list = []

        for cve_id, details in cve_details.items():
            severity_score = 4.0 if details["is_critical"] else 3.0
            risk_score = calculate_risk_score(
                base_severity=severity_score,
                is_exploited=details["is_exploited"],
                mentions=details["mentions"]
            )

            cve_list.append({
                "cve_id": cve_id,
                "mentions": details["mentions"],
                "severity": "critical" if details["is_critical"] else "high",
                "exploited": details["is_exploited"],
                "risk_score": round(risk_score, 2),
                "affected_vendors": list(details["vendors"])
            })

        # Sort by risk score descending
        cve_list.sort(key=lambda x: x["risk_score"], reverse=True)
        return cve_list


class ThreatActorAnalyzer(BaseAnalyzer):
    """Analyzes threat actor activity and timeline."""

    def __init__(self, config: TrendsConfig, threat_actor_names: List[str]):
        """
        Initialize with threat actor names.

        Args:
            config: TrendsConfig instance
            threat_actor_names: List of known threat actor names
        """
        super().__init__(config)
        self.threat_actor_names = threat_actor_names

    def analyze(self, items: List[Dict]) -> Dict[str, Any]:
        """
        Analyze threat actor activity and timeline.

        Args:
            items: News items to analyze

        Returns:
            Dict with most active actors, timeline data
        """
        actor_mentions = Counter()
        actor_timeline = defaultdict(lambda: {"count": 0, "actors": Counter()})

        # Count actor mentions and build timeline
        for item in items:
            text = self._extract_text(item)
            pub_ts = item.get("published_ts", 0)
            date_str = datetime.fromtimestamp(pub_ts, tz=timezone.utc).date().isoformat()

            for actor in self.threat_actor_names:
                if actor.lower() in text:
                    actor_mentions[actor] += 1
                    actor_timeline[date_str]["count"] += 1
                    actor_timeline[date_str]["actors"][actor] += 1

        # Build most active actors list
        most_active = [
            {
                "name": actor,
                "mentions": count,
                "risk_level": self._get_risk_level(count)
            }
            for actor, count in actor_mentions.most_common(15)
        ]

        # Format timeline
        timeline = [
            {
                "date": date_str,
                "count": data["count"],
                "top_actors": [[actor, count] for actor, count in data["actors"].most_common(5)]
            }
            for date_str, data in sorted(actor_timeline.items())
        ]

        return {
            "most_active": most_active,
            "total_unique": len(actor_mentions),
            "timeline": timeline[-30:]  # Last 30 days
        }

    def _get_risk_level(self, mentions: int) -> str:
        """Determine risk level based on mention count."""
        if mentions > 10:
            return "high"
        elif mentions > 5:
            return "medium"
        else:
            return "low"


class AttackSurfaceAnalyzer(BaseAnalyzer):
    """Analyzes attack surfaces with severity distribution and risk weighting."""

    def analyze(self, items: List[Dict]) -> Dict[str, Any]:
        """
        Analyze attack surfaces from news items.

        Args:
            items: News items to analyze

        Returns:
            Dict of attack surfaces with incident counts and risk scores
        """
        surface_data = {}

        for surface_key, surface_config in self.config.attack_surfaces.items():
            count = 0
            severity_counts = Counter()

            for item in items:
                text = self._extract_text(item)

                # Check if item relates to this attack surface
                if self._surface_matches(text, surface_config["keywords"]):
                    count += 1

                    # Determine severity from text
                    severity = self._determine_severity(text)
                    severity_counts[severity] += 1

            if count > 0:
                surface_data[surface_key] = {
                    "label": surface_config["label"],
                    "incidents": count,
                    "severity_distribution": dict(severity_counts),
                    "risk_multiplier": surface_config["severity_multiplier"],
                    "risk_score": round(count * surface_config["severity_multiplier"] / 10, 2)
                }

        # Sort by risk score
        return dict(sorted(
            surface_data.items(),
            key=lambda x: x[1]["risk_score"],
            reverse=True
        ))

    def _surface_matches(self, text: str, keywords: List[str]) -> bool:
        """Check if text matches attack surface keywords."""
        return any(keyword.lower() in text for keyword in keywords)

    def _determine_severity(self, text: str) -> str:
        """Determine severity level from text."""
        if any(k in text for k in ["critical", "severe", "high"]):
            return "high"
        elif any(k in text for k in ["medium", "moderate"]):
            return "medium"
        else:
            return "low"
