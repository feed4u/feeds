// Modern trends data types for enhanced cybersecurity intelligence

export interface TrendsSummary {
  total_articles: number;
  time_range_days: number;
  critical_alerts: number;
  trending_threats: number;
  risk_score: number;
  risk_level: "critical" | "elevated" | "moderate" | "low";
  total_cves: number;
  exploited_cves: number;
}

export interface AttackPattern {
  name: string;
  key: string;
  severity: "critical" | "high" | "medium" | "low";
  count: number;
  velocity: "surging" | "rising" | "stable" | "declining";
  change_percent: number;
  risk_score: number;
  mitre_techniques: string[];
  description: string;
}

export interface CVEDetail {
  cve_id: string;
  mentions: number;
  severity: "critical" | "high" | "medium" | "low";
  exploited: boolean;
  risk_score: number;
  affected_vendors: string[];
}

export interface CVEAnalysis {
  top_cves: CVEDetail[];
  by_severity: {
    critical: { count: number; exploited: number };
    high: { count: number; exploited: number };
  };
  total_unique: number;
  total_exploited: number;
}

export interface ThreatActor {
  name: string;
  mentions: number;
  risk_level: "high" | "medium" | "low";
}

export interface ThreatActorTimeline {
  date: string;
  count: number;
  top_actors: Array<[string, number]>;
}

export interface ThreatActors {
  most_active: ThreatActor[];
  total_unique: number;
  timeline: ThreatActorTimeline[];
}

export interface Insights {
  critical_actions: string[];
  watch_list: string[];
  trending_up: string[];
}

export interface AttackSurface {
  label: string;
  incidents: number;
  severity_distribution: {
    low?: number;
    medium?: number;
    high?: number;
  };
  risk_multiplier: number;
  risk_score: number;
}

export interface Comparisons {
  week_over_week: {
    total_volume: {
      current: number;
      previous: number;
      change_percent: number;
      change_label: string;
    };
    critical_threats: {
      current: number;
      change_label: string;
    };
  };
}

export interface TrendsData {
  generated_at: string;
  version: string;
  summary: TrendsSummary;
  threat_intelligence: {
    attack_patterns: AttackPattern[];
  };
  cve_analysis: CVEAnalysis;
  threat_actors: ThreatActors;
  attack_surface: Record<string, AttackSurface>;
  comparisons: Comparisons;
  insights: Insights;
  windows: string[];
}

import { dataUrl } from "./dataPaths";

export async function fetchTrendsData(): Promise<TrendsData> {
  const response = await fetch(dataUrl("trends.json"), {
    headers: {
      "Cache-Control": "no-cache",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch trends data (${response.status})`);
  }

  const rawData = await response.json();

  // Adapter: Transform simple backend structure to complex frontend structure
  return transformTrendsData(rawData);
}

// Transform trends.json to TrendsData structure expected by UI
function transformTrendsData(raw: any): TrendsData {
  // Check if this is the new format (has threat_intelligence key)
  if (raw.threat_intelligence) {
    // New format - pass through with minimal transformation
    return {
      generated_at: raw.generated_at,
      version: raw.version || "2.1",
      summary: raw.summary,
      threat_intelligence: raw.threat_intelligence,
      cve_analysis: raw.cve_analysis,
      threat_actors: raw.threat_actors,
      attack_surface: raw.attack_surface || {},
      comparisons: raw.comparisons,
      insights: {
        critical_actions: raw.insights?.critical_actions || [],
        watch_list: raw.insights?.watch_list || [],
        trending_up: raw.insights?.trending_up || [],
      },
      windows: raw.windows || ["24h", "7d", "30d", "90d"],
    };
  }

  // Legacy format transformation (kept for backwards compatibility)
  const summary: TrendsSummary = {
    total_articles: raw.daily_volume?.reduce((sum: number, day: any) => sum + day.count, 0) || 0,
    time_range_days: 90,
    critical_alerts: 0,
    trending_threats: Object.keys(raw.trending_terms || {}).length,
    risk_score: 50,
    risk_level: "moderate",
    total_cves: Object.values(raw.top_cves?.["30d"] || []).length,
    exploited_cves: 0,
  };

  const attackPatterns: AttackPattern[] = Object.entries(raw.trending_terms || {}).slice(0, 10).map(([key, value]: [string, any]) => ({
    name: value.label || key,
    key,
    severity: "medium" as const,
    count: value.counts?.["30d"] || 0,
    velocity: "stable" as const,
    change_percent: 0,
    risk_score: 50,
    mitre_techniques: [],
    description: `Trending: ${value.label || key}`,
  }));

  const topCves: CVEDetail[] = (raw.top_cves?.["30d"] || []).slice(0, 20).map(([cve, count]: [string, number]) => ({
    cve_id: cve,
    mentions: count,
    severity: "medium" as const,
    exploited: false,
    risk_score: count * 10,
    affected_vendors: [],
  }));

  const cveAnalysis: CVEAnalysis = {
    top_cves: topCves,
    by_severity: {
      critical: { count: 0, exploited: 0 },
      high: { count: topCves.length, exploited: 0 },
    },
    total_unique: topCves.length,
    total_exploited: 0,
  };

  const actorMap = (raw.threat_actor_daily || [])
    .flatMap((day: any) => day.top_actors || [])
    .reduce((acc: Map<string, number>, [name, count]: [string, number]) => {
      acc.set(name, (acc.get(name) || 0) + count);
      return acc;
    }, new Map());

  const mostActive = Array.from(actorMap.entries())
    .map(([name, mentions]: [string, number]) => ({
      name,
      mentions,
      risk_level: mentions > 10 ? "high" as const : mentions > 5 ? "medium" as const : "low" as const,
    }))
    .sort((a, b) => b.mentions - a.mentions)
    .slice(0, 50);

  const threatActors: ThreatActors = {
    total_unique: actorMap.size,
    most_active: mostActive,
    timeline: raw.threat_actor_daily || [],
  };

  return {
    generated_at: raw.generated_at,
    version: "1.0",
    summary,
    threat_intelligence: {
      attack_patterns: attackPatterns,
    },
    cve_analysis: cveAnalysis,
    threat_actors: threatActors,
    attack_surface: {},
    comparisons: {
      week_over_week: {
        total_volume: {
          current: 0,
          previous: 0,
          change_percent: 0,
          change_label: "stable",
        },
        critical_threats: {
          current: 0,
          change_label: "stable",
        },
      },
    },
    insights: {
      critical_actions: [],
      watch_list: [],
      trending_up: [],
    },
    windows: raw.windows || ["24h", "7d", "30d", "90d"],
  };
}

// Helper to get risk level color
export function getRiskLevelColor(level: string): string {
  const colors: Record<string, string> = {
    critical: "text-red-600 dark:text-red-400",
    elevated: "text-orange-600 dark:text-orange-400",
    moderate: "text-yellow-600 dark:text-yellow-400",
    low: "text-green-600 dark:text-green-400",
  };
  return colors[level] || colors.moderate;
}

// Helper to get velocity icon
export function getVelocityIcon(velocity: string): string {
  const icons: Record<string, string> = {
    surging: "⬆️",
    rising: "↗️",
    stable: "→",
    declining: "↘️",
  };
  return icons[velocity] || icons.stable;
}

// Helper to get severity badge color
export function getSeverityColor(severity: string): string {
  const colors: Record<string, string> = {
    critical: "bg-red-600 text-white",
    high: "bg-orange-600 text-white",
    medium: "bg-yellow-600 text-white",
    low: "bg-blue-600 text-white",
  };
  return colors[severity] || colors.medium;
}
