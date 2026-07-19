"""
Actionable insights generator for threat intelligence.

This module generates AI-driven recommendations based on trends analysis:
- Critical actions requiring immediate attention
- Watch list items for monitoring
- Trending threats (up and down)
- Strategic recommendations
"""

from typing import Any, Dict, List


class InsightsGenerator:
    """Generates actionable insights from trends analysis."""

    def __init__(self, max_critical: int = 5, max_watch: int = 6, max_trending: int = 5):
        """
        Initialize insights generator.

        Args:
            max_critical: Maximum critical actions to generate
            max_watch: Maximum watch list items to generate
            max_trending: Maximum trending items to track
        """
        self.max_critical = max_critical
        self.max_watch = max_watch
        self.max_trending = max_trending

    def generate(
        self,
        summary: Dict[str, Any],
        attack_patterns: List[Dict],
        cve_analysis: Dict[str, Any],
        attack_surface: Dict[str, Any],
        threat_actors: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Generate actionable insights from all analysis components.

        Args:
            summary: Executive summary with KPIs
            attack_patterns: Attack pattern analysis results
            cve_analysis: CVE analysis results
            attack_surface: Attack surface analysis results
            threat_actors: Threat actor analysis results

        Returns:
            Dict with critical_actions, watch_list, trending_up, trending_down
        """
        critical_actions = []
        watch_list = []
        trending_up = []
        trending_down = []

        # Generate CVE-based critical actions
        critical_actions.extend(
            self._generate_cve_actions(cve_analysis)
        )

        # Generate attack pattern insights
        pattern_insights = self._generate_pattern_insights(attack_patterns)
        watch_list.extend(pattern_insights["watch"])
        trending_up.extend(pattern_insights["trending_up"])
        trending_down.extend(pattern_insights["trending_down"])

        # Generate attack surface recommendations
        watch_list.extend(
            self._generate_surface_recommendations(attack_surface)
        )

        # Generate threat actor warnings
        watch_list.extend(
            self._generate_actor_warnings(threat_actors)
        )

        # Add risk level warning if needed
        if summary["risk_level"] in ["critical", "elevated"]:
            critical_actions.insert(
                0,
                f"⚠️ Elevated threat environment - risk score {summary['risk_score']}/10"
            )

        # Add exploitation trend warning
        if cve_analysis["total_exploited"] > 0:
            exploit_rate = (cve_analysis["total_exploited"] / cve_analysis["total_unique"]) * 100
            if exploit_rate > 70:
                critical_actions.insert(
                    0,
                    f"🚨 High exploitation rate: {exploit_rate:.0f}% of CVEs actively exploited"
                )

        return {
            "critical_actions": critical_actions[:self.max_critical],
            "watch_list": watch_list[:self.max_watch],
            "trending_up": trending_up[:self.max_trending],
            "trending_down": trending_down[:self.max_trending]
        }

    def _generate_cve_actions(self, cve_analysis: Dict[str, Any]) -> List[str]:
        """Generate critical actions based on CVE analysis."""
        actions = []

        # High-risk exploited CVEs
        exploited_cves = [
            cve for cve in cve_analysis["top_cves"][:5]
            if cve["exploited"]
        ]

        for cve in exploited_cves:
            action = f"Patch {cve['cve_id']} immediately - actively exploited (risk: {cve['risk_score']}/10)"
            if cve["affected_vendors"]:
                action += f" [{', '.join(cve['affected_vendors'][:2])}]"
            actions.append(action)

        return actions

    def _generate_pattern_insights(self, attack_patterns: List[Dict]) -> Dict[str, List[str]]:
        """Generate insights from attack patterns."""
        watch = []
        trending_up = []
        trending_down = []

        for pattern in attack_patterns:
            velocity = pattern["velocity"]
            change = pattern["change_percent"]

            # Surging threats
            if velocity == "surging":
                watch.append(
                    f"⬆️ Monitor {pattern['name']} - surging {change:+.0f}% (risk: {pattern['risk_score']}/10)"
                )
                trending_up.append(pattern["name"])

            # Rising threats
            elif velocity == "rising":
                watch.append(
                    f"↗️ Track {pattern['name']} - rising {change:+.0f}%"
                )
                trending_up.append(pattern["name"])

            # Declining threats (still worth noting)
            elif velocity == "declining" and change < -30:
                trending_down.append(pattern["name"])

        return {
            "watch": watch,
            "trending_up": trending_up,
            "trending_down": trending_down
        }

    def _generate_surface_recommendations(self, attack_surface: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on attack surface analysis."""
        recommendations = []

        # Sort by risk score
        top_surfaces = sorted(
            attack_surface.items(),
            key=lambda x: x[1]["risk_score"],
            reverse=True
        )[:2]

        for surface_key, surface_data in top_surfaces:
            risk_score = surface_data["risk_score"]
            incidents = surface_data["incidents"]

            # High severity distribution check
            severity_dist = surface_data["severity_distribution"]
            high_count = severity_dist.get("high", 0)
            high_pct = (high_count / incidents * 100) if incidents > 0 else 0

            if risk_score > 40:
                rec = f"🔴 Review {surface_data['label']} - {incidents} incidents (risk: {risk_score})"
            elif risk_score > 25:
                rec = f"🟠 Monitor {surface_data['label']} - {incidents} incidents"
            else:
                continue

            # Add severity note if high percentage of high-severity
            if high_pct > 60:
                rec += f" ({high_pct:.0f}% high severity)"

            recommendations.append(rec)

        return recommendations

    def _generate_actor_warnings(self, threat_actors: Dict[str, Any]) -> List[str]:
        """Generate warnings based on threat actor activity."""
        warnings = []

        # Most active actors
        top_actors = threat_actors["most_active"][:3]

        for actor_data in top_actors:
            if actor_data["risk_level"] == "high":
                warnings.append(
                    f"👁️ Monitor {actor_data['name']} - {actor_data['mentions']} mentions (high activity)"
                )

        return warnings

    def generate_executive_summary(
        self,
        summary: Dict[str, Any],
        attack_patterns: List[Dict],
        cve_analysis: Dict[str, Any]
    ) -> str:
        """
        Generate executive summary text.

        Args:
            summary: Executive summary data
            attack_patterns: Attack pattern analysis
            cve_analysis: CVE analysis

        Returns:
            Formatted executive summary string
        """
        lines = []

        # Risk assessment
        risk_emoji = "🔴" if summary["risk_level"] == "critical" else "🟠" if summary["risk_level"] == "elevated" else "🟡"
        lines.append(
            f"{risk_emoji} Overall Risk: {summary['risk_score']}/10 ({summary['risk_level'].upper()})"
        )

        # CVE summary
        lines.append(
            f"🔍 {summary['total_cves']} unique CVEs identified, {summary['exploited_cves']} actively exploited"
        )

        # Threat summary
        critical_count = summary["critical_alerts"]
        trending_count = summary["trending_threats"]
        lines.append(
            f"⚡ {critical_count} critical alerts, {trending_count} trending threats"
        )

        # Top threat
        if attack_patterns:
            top_threat = attack_patterns[0]
            lines.append(
                f"🎯 Top Threat: {top_threat['name']} (risk: {top_threat['risk_score']}/10, {top_threat['velocity']})"
            )

        return "\n".join(lines)

    def generate_recommendations_by_persona(
        self,
        insights: Dict[str, List[str]],
        summary: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Generate role-specific recommendations.

        Args:
            insights: Generated insights
            summary: Executive summary

        Returns:
            Dict with recommendations for different personas (CISO, SOC, Admins)
        """
        recommendations = {
            "ciso": [],
            "soc": [],
            "admins": []
        }

        # CISO level (strategic)
        if summary["risk_level"] in ["critical", "elevated"]:
            recommendations["ciso"].append(
                f"Consider escalating security posture - environment at {summary['risk_level'].upper()} risk"
            )

        if insights["trending_up"]:
            recommendations["ciso"].append(
                f"Emerging threats detected: {', '.join(insights['trending_up'][:3])}"
            )

        # SOC level (tactical)
        recommendations["soc"].extend(insights["critical_actions"])
        recommendations["soc"].extend(insights["watch_list"][:3])

        # Admin level (operational)
        # Focus on patching and configuration
        patch_actions = [
            action for action in insights["critical_actions"]
            if "patch" in action.lower()
        ]
        recommendations["admins"].extend(patch_actions)

        return recommendations
