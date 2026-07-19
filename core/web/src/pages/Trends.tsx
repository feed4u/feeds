import { useState, useEffect } from "react";
import { vertical } from "@/config/verticals";
import { Link } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Helmet } from "react-helmet-async";
import { format } from "date-fns";
import { TrendingUp, AlertTriangle, Shield, Activity, Target } from "lucide-react";
import {
  fetchTrendsData,
  TrendsData,
  getRiskLevelColor,
  getVelocityIcon,
  getSeverityColor,
} from "@/data/trendsData";

export default function Trends() {
  const [trends, setTrends] = useState<TrendsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const data = await fetchTrendsData();
        setTrends(data);
        setError(null);
      } catch (err) {
        console.error("Failed to load trends data:", err);
        setError("Could not load trends data.");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  if (loading) {
    return (
      <Layout>
        <div className="text-center py-12 bg-card rounded-lg border border-border">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent mb-4" />
          <p className="text-[15px] text-muted-foreground font-mono">Loading intelligence...</p>
        </div>
      </Layout>
    );
  }

  if (error || !trends) {
    return (
      <Layout>
        <div className="text-center py-12 bg-card rounded-lg border border-destructive">
          <p className="text-[15px] text-destructive font-mono">{error || "No data available"}</p>
        </div>
      </Layout>
    );
  }

  const { summary, threat_intelligence, cve_analysis, threat_actors, insights, attack_surface, comparisons } = trends;

  return (
    <Layout>
      <Helmet>
        <title>Threat Intelligence — {vertical.metaTitle}</title>
        <meta
          name="description"
          content="Comprehensive cybersecurity threat intelligence with risk scoring and actionable insights"
        />
      </Helmet>

      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <Shield className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-3xl font-bold text-foreground">Threat Intelligence</h1>
              <p className="text-[15px] text-muted-foreground">
                {summary.time_range_days}-day analysis • Updated {format(new Date(trends.generated_at), "MMM d, HH:mm")}
              </p>
            </div>
          </div>
        </div>

        {/* Risk Score Hero */}
        <Card className="p-8 bg-gradient-to-br from-card to-muted border-border">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="text-center md:text-left">
              <p className="text-sm font-mono text-muted-foreground uppercase mb-2">Threat Environment</p>
              <div className="flex items-baseline gap-3">
                <span className={`text-6xl font-bold ${getRiskLevelColor(summary.risk_level)}`}>
                  {summary.risk_score}
                </span>
                <span className="text-2xl text-muted-foreground">/10</span>
              </div>
              <p className={`text-xl font-semibold mt-2 uppercase ${getRiskLevelColor(summary.risk_level)}`}>
                {summary.risk_level}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 bg-background rounded-lg">
                <p className="text-2xl font-bold text-red-600">{summary.critical_alerts}</p>
                <p className="text-sm text-muted-foreground">Critical Alerts</p>
              </div>
              <div className="text-center p-4 bg-background rounded-lg">
                <p className="text-2xl font-bold text-orange-600">{summary.trending_threats}</p>
                <p className="text-sm text-muted-foreground">Trending Threats</p>
              </div>
              <div className="text-center p-4 bg-background rounded-lg">
                <p className="text-2xl font-bold text-foreground">{summary.total_cves}</p>
                <p className="text-sm text-muted-foreground">Unique CVEs</p>
              </div>
              <div className="text-center p-4 bg-background rounded-lg">
                <p className="text-2xl font-bold text-red-600">{summary.exploited_cves}</p>
                <p className="text-sm text-muted-foreground">Exploited</p>
              </div>
            </div>
          </div>
        </Card>

        {/* Critical Actions */}
        {insights.critical_actions.length > 0 && (
          <Card className="p-5 bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <h2 className="text-lg font-semibold text-red-900 dark:text-red-100">Critical Actions Required</h2>
            </div>
            <ul className="space-y-2">
              {insights.critical_actions.map((action, idx) => (
                <li key={idx} className="flex items-start gap-2 text-[15px] text-red-800 dark:text-red-200">
                  <span className="text-red-600 font-bold mt-0.5">•</span>
                  <span>{action}</span>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {/* Attack Patterns */}
        <Card className="p-5">
          <h2 className="text-xl font-semibold text-foreground mb-4 flex items-center gap-2">
            <Target className="h-5 w-5" />
            Attack Patterns
          </h2>
          <div className="space-y-3">
            {threat_intelligence.attack_patterns.slice(0, 8).map((pattern) => (
              <div key={pattern.key} className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                <div className="text-2xl">{getVelocityIcon(pattern.velocity)}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-foreground">{pattern.name}</span>
                    <Badge className={`text-xs ${getSeverityColor(pattern.severity)}`}>
                      {pattern.severity}
                    </Badge>
                    {pattern.velocity !== "stable" && (
                      <span className="text-xs text-muted-foreground">
                        {pattern.change_percent > 0 ? "+" : ""}{pattern.change_percent.toFixed(0)}%
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{pattern.description}</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-foreground">{pattern.count}</p>
                  <p className="text-xs text-muted-foreground">mentions</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold text-red-600">{pattern.risk_score.toFixed(1)}</p>
                  <p className="text-xs text-muted-foreground">risk</p>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* CVE Analysis */}
          <Card className="p-5">
            <h2 className="text-xl font-semibold text-foreground mb-4">CVE Analysis</h2>

            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="p-3 bg-red-50 dark:bg-red-950/20 rounded-lg">
                <p className="text-sm text-muted-foreground">Critical</p>
                <p className="text-2xl font-bold text-red-600">{cve_analysis.by_severity.critical.count}</p>
                <p className="text-xs text-muted-foreground">
                  {cve_analysis.by_severity.critical.exploited} exploited
                </p>
              </div>
              <div className="p-3 bg-orange-50 dark:bg-orange-950/20 rounded-lg">
                <p className="text-sm text-muted-foreground">High</p>
                <p className="text-2xl font-bold text-orange-600">{cve_analysis.by_severity.high.count}</p>
                <p className="text-xs text-muted-foreground">
                  {cve_analysis.by_severity.high.exploited} exploited
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-semibold text-foreground mb-2">Top CVEs (Risk Scored)</p>
              {cve_analysis.top_cves.slice(0, 8).map((cve) => (
                <div key={cve.cve_id} className="flex items-center justify-between p-2 bg-muted/50 rounded">
                  <div className="flex items-center gap-2">
                    <a
                      href={`https://nvd.nist.gov/vuln/detail/${cve.cve_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline font-mono text-sm"
                    >
                      {cve.cve_id}
                    </a>
                    {cve.exploited && (
                      <Badge className="text-xs bg-red-600">EXPLOITED</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground">{cve.mentions} mentions</span>
                    <span className="text-sm font-bold text-red-600">{cve.risk_score.toFixed(1)}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Threat Actors */}
          <Card className="p-5">
            <h2 className="text-xl font-semibold text-foreground mb-4">Threat Actor Activity</h2>
            <p className="text-sm text-muted-foreground mb-4">
              {threat_actors.total_unique} unique actors detected
            </p>
            <div className="space-y-2">
              {threat_actors.most_active.slice(0, 12).map((actor) => {
                return (
                  <div key={actor.name} className="flex items-center justify-between p-2 bg-muted/50 rounded">
                    <Link
                      to={`/threat-actor/${encodeURIComponent(actor.name)}`}
                      className="font-mono text-sm text-primary hover:underline"
                    >
                      {actor.name}
                    </Link>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className={`text-xs ${
                          actor.risk_level === "high"
                            ? "border-red-600 text-red-600"
                            : actor.risk_level === "medium"
                            ? "border-orange-600 text-orange-600"
                            : "border-blue-600 text-blue-600"
                        }`}
                      >
                        {actor.risk_level}
                      </Badge>
                      <span className="text-sm font-mono text-muted-foreground">{actor.mentions}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        {/* Week-over-Week Comparison */}
        {comparisons && (
          <Card className="p-5">
            <h2 className="text-xl font-semibold text-foreground mb-4 flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Week-over-Week Trends
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-muted/50 rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">Article Volume</p>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-foreground">
                    {comparisons.week_over_week.total_volume.current}
                  </span>
                  <span className="text-sm text-muted-foreground">articles this week</span>
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <span className={`text-sm font-semibold ${
                    comparisons.week_over_week.total_volume.change_percent > 0
                      ? "text-red-600"
                      : "text-green-600"
                  }`}>
                    {comparisons.week_over_week.total_volume.change_percent > 0 ? "↑" : "↓"}{" "}
                    {Math.abs(comparisons.week_over_week.total_volume.change_percent)}%
                  </span>
                  <span className="text-xs text-muted-foreground">
                    vs last week ({comparisons.week_over_week.total_volume.previous})
                  </span>
                </div>
              </div>
              <div className="p-4 bg-red-50 dark:bg-red-950/20 rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">Critical Threats</p>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-red-600">
                    {comparisons.week_over_week.critical_threats.current}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {comparisons.week_over_week.critical_threats.change_label}
                  </span>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Threat Actor Timeline */}
        {threat_actors.timeline && threat_actors.timeline.length > 0 && (
          <Card className="p-5">
            <h2 className="text-xl font-semibold text-foreground mb-4">Threat Actor Activity Timeline</h2>
            <p className="text-sm text-muted-foreground mb-4">
              Last 30 days of threat actor mentions
            </p>
            <div className="space-y-2">
              {threat_actors.timeline.slice(-14).map((day) => (
                <div key={day.date} className="flex items-center gap-3">
                  <span className="text-sm text-muted-foreground font-mono w-24">
                    {format(new Date(day.date), "MMM d")}
                  </span>
                  <div className="flex-1">
                    <div
                      className="h-8 bg-red-600/20 border-l-4 border-red-600 rounded-r flex items-center px-3"
                      style={{ width: `${Math.min((day.count / 20) * 100, 100)}%` }}
                    >
                      <span className="text-sm font-semibold text-foreground">{day.count}</span>
                    </div>
                  </div>
                  <div className="flex gap-1 text-xs text-muted-foreground">
                    {day.top_actors.slice(0, 3).map(([actor]) => {
                      return (
                        <Link key={actor} to={`/threat-actor/${encodeURIComponent(actor)}`}>
                          <Badge variant="outline" className="text-xs hover:bg-muted cursor-pointer">
                            {actor}
                          </Badge>
                        </Link>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Attack Surface Heat Map */}
        {attack_surface && Object.keys(attack_surface).length > 0 && (
          <Card className="p-5">
            <h2 className="text-xl font-semibold text-foreground mb-4">Attack Surface Analysis</h2>
            <p className="text-sm text-muted-foreground mb-4">
              Risk-weighted incident distribution across attack surfaces
            </p>
            <div className="space-y-3">
              {Object.entries(attack_surface)
                .sort((a, b) => b[1].risk_score - a[1].risk_score)
                .map(([key, surface]) => {
                  const total = surface.incidents;
                  const highPct = ((surface.severity_distribution.high || 0) / total) * 100;
                  const mediumPct = ((surface.severity_distribution.medium || 0) / total) * 100;
                  const lowPct = ((surface.severity_distribution.low || 0) / total) * 100;

                  return (
                    <div key={key} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="font-semibold text-foreground">{surface.label}</span>
                          <span className="text-sm text-muted-foreground ml-2">
                            ({surface.incidents} incidents)
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-mono text-muted-foreground">
                            Risk: {surface.risk_score.toFixed(1)}
                          </span>
                          <div
                            className={`w-3 h-3 rounded-full ${
                              surface.risk_score > 40
                                ? "bg-red-600"
                                : surface.risk_score > 25
                                ? "bg-orange-600"
                                : "bg-yellow-600"
                            }`}
                          />
                        </div>
                      </div>
                      <div className="h-6 bg-muted rounded-full overflow-hidden flex">
                        {highPct > 0 && (
                          <div
                            className="bg-red-600 flex items-center justify-center text-xs text-white font-semibold"
                            style={{ width: `${highPct}%` }}
                            title={`High: ${surface.severity_distribution.high}`}
                          >
                            {highPct > 15 && `${surface.severity_distribution.high}`}
                          </div>
                        )}
                        {mediumPct > 0 && (
                          <div
                            className="bg-orange-600 flex items-center justify-center text-xs text-white font-semibold"
                            style={{ width: `${mediumPct}%` }}
                            title={`Medium: ${surface.severity_distribution.medium}`}
                          >
                            {mediumPct > 15 && `${surface.severity_distribution.medium}`}
                          </div>
                        )}
                        {lowPct > 0 && (
                          <div
                            className="bg-yellow-600 flex items-center justify-center text-xs text-white font-semibold"
                            style={{ width: `${lowPct}%` }}
                            title={`Low: ${surface.severity_distribution.low}`}
                          >
                            {lowPct > 15 && `${surface.severity_distribution.low}`}
                          </div>
                        )}
                      </div>
                      <div className="flex gap-3 text-xs text-muted-foreground">
                        <span>🔴 High: {surface.severity_distribution.high || 0}</span>
                        <span>🟠 Medium: {surface.severity_distribution.medium || 0}</span>
                        <span>🟡 Low: {surface.severity_distribution.low || 0}</span>
                      </div>
                    </div>
                  );
                })}
            </div>
          </Card>
        )}

        {/* Watch List */}
        {insights.watch_list.length > 0 && (
          <Card className="p-5 bg-orange-50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-800">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="h-5 w-5 text-orange-600" />
              <h2 className="text-lg font-semibold text-orange-900 dark:text-orange-100">Watch List</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              {insights.watch_list.map((item, idx) => (
                <Badge key={idx} className="bg-orange-600 text-white">
                  {item}
                </Badge>
              ))}
            </div>
          </Card>
        )}
      </div>
    </Layout>
  );
}
