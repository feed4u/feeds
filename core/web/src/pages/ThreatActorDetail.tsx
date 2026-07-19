import { useParams, Link } from "react-router-dom";
import { vertical } from "@/config/verticals";
import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Helmet } from "react-helmet-async";
import { Shield, ExternalLink, ArrowLeft, Target, AlertTriangle, Lightbulb } from "lucide-react";
import { getActorProfile } from "@/data/threatActorProfiles";
import { getTaxonomyForActor } from "@/data/threatActorTaxonomies";

export default function ThreatActorDetail() {
  const { actorName } = useParams<{ actorName: string }>();

  if (!actorName) {
    return (
      <Layout>
        <div className="text-center py-12 bg-card rounded-lg border border-destructive">
          <p className="text-[15px] text-destructive font-mono">Actor name not provided</p>
          <Link to="/trends">
            <Button variant="outline" className="mt-4">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Trends
            </Button>
          </Link>
        </div>
      </Layout>
    );
  }

  const profile = getActorProfile(actorName);
  const taxonomy = getTaxonomyForActor(actorName);

  return (
    <Layout>
      <Helmet>
        <title>{`${actorName} — Threat Actor Profile — ${vertical.metaTitle}`}</title>
        <meta
          name="description"
          content={profile?.summary || `Threat actor profile for ${actorName}`}
        />
      </Helmet>

      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Shield className="h-8 w-8 text-destructive" />
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-3xl font-bold text-foreground">{actorName}</h1>
                <Link to={`/threat-actors/${taxonomy.id}`}>
                  <Badge variant="outline" className="text-[13px] cursor-pointer hover:bg-muted">
                    {taxonomy.name}
                  </Badge>
                </Link>
              </div>
              <p className="text-[15px] text-muted-foreground mt-1">
                Threat Actor Profile & Intelligence
              </p>
            </div>
          </div>
          <Link to="/trends">
            <Button variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Trends
            </Button>
          </Link>
        </div>

        {profile ? (
          <>
            {/* Summary */}
            <Card className="p-6 bg-gradient-to-br from-card to-muted border-border">
              <div className="flex items-start gap-3">
                <Target className="h-6 w-6 text-destructive mt-1 flex-shrink-0" />
                <div>
                  <h2 className="text-xl font-semibold text-foreground mb-3">Overview</h2>
                  <p className="text-[15px] text-muted-foreground leading-relaxed">
                    {profile.summary}
                  </p>
                </div>
              </div>
            </Card>

            {/* Notable Attacks */}
            {profile.notableAttacks && profile.notableAttacks.length > 0 && (
              <Card className="p-6">
                <div className="flex items-start gap-3 mb-4">
                  <AlertTriangle className="h-6 w-6 text-destructive mt-1" />
                  <div>
                    <h2 className="text-xl font-semibold text-foreground mb-3">Notable Attacks</h2>
                    <ul className="list-disc pl-6 space-y-2">
                      {profile.notableAttacks.map((attack, idx) => (
                        <li key={idx} className="text-[15px] text-muted-foreground">
                          {attack}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </Card>
            )}

            {/* Unique Methods & TTPs */}
            {profile.uniqueMethods && profile.uniqueMethods.length > 0 && (
              <Card className="p-6 bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800">
                <div className="flex items-start gap-3 mb-4">
                  <Lightbulb className="h-6 w-6 text-amber-600 dark:text-amber-500 mt-1" />
                  <div>
                    <h2 className="text-xl font-semibold text-foreground mb-3">
                      Unique Methods & TTPs
                    </h2>
                    <ul className="list-disc pl-6 space-y-2">
                      {profile.uniqueMethods.map((method, idx) => (
                        <li key={idx} className="text-[15px] text-muted-foreground">
                          {method}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </Card>
            )}

            {/* Official Sources */}
            <Card className="p-6">
              <h2 className="text-xl font-semibold text-foreground mb-4">
                Official Sources & Intelligence Reports
              </h2>
              <div className="space-y-4">
                {profile.sources.map((source, idx) => (
                  <div
                    key={idx}
                    className="p-4 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <h3 className="font-semibold text-foreground mb-1">{source.name}</h3>
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-primary hover:underline inline-flex items-center gap-1 font-mono break-all"
                        >
                          {source.url}
                          <ExternalLink className="h-3 w-3 flex-shrink-0" />
                        </a>
                      </div>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Button variant="outline" size="sm">
                          <ExternalLink className="h-4 w-4 mr-2" />
                          Visit
                        </Button>
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </>
        ) : (
          /* No profile available - show taxonomy info */
          <Card className="p-6">
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-semibold text-foreground mb-2">
                  Actor Profile Not Available
                </h2>
                <p className="text-[15px] text-muted-foreground">
                  We don't have a detailed profile for <strong>{actorName}</strong> yet.
                  However, based on the naming convention, this actor belongs to the{" "}
                  <Link
                    to={`/threat-actors/${taxonomy.id}`}
                    className="text-primary hover:underline font-semibold"
                  >
                    {taxonomy.name}
                  </Link>{" "}
                  taxonomy.
                </p>
              </div>

              <div className="pt-4 border-t border-border">
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                  Research This Actor
                </h3>
                <div className="space-y-2">
                  <a
                    href={`https://attack.mitre.org/groups/?general-filter=${encodeURIComponent(actorName)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">MITRE ATT&CK Groups</span>
                      <ExternalLink className="h-4 w-4" />
                    </div>
                  </a>
                  <a
                    href={`https://www.google.com/search?q=${encodeURIComponent(actorName + " threat actor")}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Google Search</span>
                      <ExternalLink className="h-4 w-4" />
                    </div>
                  </a>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Taxonomy Context */}
        <Card className="p-6 bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800">
          <h2 className="text-xl font-semibold text-foreground mb-3">
            About {taxonomy.name}
          </h2>
          <p className="text-[15px] text-muted-foreground leading-relaxed mb-4">
            {taxonomy.description}
          </p>
          <Link to={`/threat-actors/${taxonomy.id}`}>
            <Button variant="outline" size="sm">
              Learn More About {taxonomy.name}
              <ArrowLeft className="h-4 w-4 ml-2 rotate-180" />
            </Button>
          </Link>
        </Card>
      </div>
    </Layout>
  );
}
