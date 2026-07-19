import { useParams, Link } from "react-router-dom";
import { vertical } from "@/config/verticals";
import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Helmet } from "react-helmet-async";
import { Shield, ExternalLink, ArrowLeft, BookOpen, Target } from "lucide-react";
import { TAXONOMIES, ThreatActorTaxonomy } from "@/data/threatActorTaxonomies";

export default function ThreatActorTaxonomyPage() {
  const { taxonomyId } = useParams<{ taxonomyId: string }>();
  const taxonomy: ThreatActorTaxonomy | undefined = taxonomyId ? TAXONOMIES[taxonomyId] : undefined;

  if (!taxonomy) {
    return (
      <Layout>
        <div className="text-center py-12 bg-card rounded-lg border border-destructive">
          <p className="text-[15px] text-destructive font-mono">Taxonomy not found</p>
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

  return (
    <Layout>
      <Helmet>
        <title>{`${taxonomy.name} — Threat Actor Taxonomy — ${vertical.metaTitle}`}</title>
        <meta
          name="description"
          content={taxonomy.description}
        />
      </Helmet>

      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Shield className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-3xl font-bold text-foreground">{taxonomy.name}</h1>
              <p className="text-[15px] text-muted-foreground mt-1">
                Threat Actor Naming Convention & Taxonomy
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

        {/* Overview */}
        <Card className="p-6 bg-gradient-to-br from-card to-muted border-border">
          <div className="flex items-start gap-3 mb-4">
            <BookOpen className="h-6 w-6 text-primary mt-1" />
            <div>
              <h2 className="text-xl font-semibold text-foreground mb-2">Overview</h2>
              <p className="text-[15px] text-muted-foreground leading-relaxed">
                {taxonomy.description}
              </p>
            </div>
          </div>
        </Card>

        {/* Naming Methodology */}
        <Card className="p-6">
          <div className="flex items-start gap-3 mb-4">
            <Target className="h-6 w-6 text-primary mt-1" />
            <div>
              <h2 className="text-xl font-semibold text-foreground mb-2">Naming Methodology</h2>
              <p className="text-[15px] text-muted-foreground leading-relaxed">
                {taxonomy.methodology}
              </p>
            </div>
          </div>

          {/* Examples */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
              Examples
            </h3>
            <div className="flex flex-wrap gap-2">
              {taxonomy.examples.map((example) => (
                <Badge
                  key={example}
                  variant="outline"
                  className="text-[15px] px-3 py-1.5 font-mono"
                >
                  {example}
                </Badge>
              ))}
            </div>
          </div>
        </Card>

        {/* Official Sources */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">
            Official Sources & Further Reading
          </h2>
          <div className="space-y-4">
            {taxonomy.sources.map((source, idx) => (
              <div
                key={idx}
                className="p-4 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h3 className="font-semibold text-foreground mb-1">{source.name}</h3>
                    <p className="text-sm text-muted-foreground mb-2">
                      {source.description}
                    </p>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary hover:underline inline-flex items-center gap-1 font-mono"
                    >
                      {source.url}
                      <ExternalLink className="h-3 w-3" />
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

        {/* Related Taxonomies */}
        <Card className="p-6 bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800">
          <h2 className="text-xl font-semibold text-foreground mb-4">
            Explore Other Taxonomies
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.values(TAXONOMIES)
              .filter(t => t.id !== taxonomy.id)
              .map((t) => (
                <Link key={t.id} to={`/threat-actors/${t.id}`}>
                  <div className="p-3 bg-background rounded-lg hover:bg-muted transition-colors cursor-pointer border border-border">
                    <h3 className="font-semibold text-foreground text-sm mb-1">
                      {t.name}
                    </h3>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {t.description.substring(0, 100)}...
                    </p>
                  </div>
                </Link>
              ))}
          </div>
        </Card>
      </div>
    </Layout>
  );
}
