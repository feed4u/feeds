// Per-vertical site configuration. Pure data — imported by both the app and
// vite.config.ts (where import.meta.env is unavailable, hence the guards).

export type VerticalId = "k5" | "4u" | "economics" | "storage" | "finnish";

export interface VerticalFeatures {
  trends: boolean;
  morningCall: boolean;
  threatActors: boolean;
  duplicates: boolean;
}

export interface VerticalConfig {
  id: VerticalId;
  logoText: { primary: string; suffix: string };
  iconName: "shield" | "cpu" | "trending-up" | "database" | "newspaper";
  heading: string;
  tagline: string;
  metaTitle: string;
  metaDescription: string;
  searchPlaceholder: string;
  footerText: string;
  features: VerticalFeatures;
}

export const VERTICALS: Record<VerticalId, VerticalConfig> = {
  k5: {
    id: "k5",
    logoText: { primary: "k5", suffix: ".ai" },
    iconName: "shield",
    heading: "Security News Feed",
    tagline:
      "Curated security news from multiple public RSS sources, pre-aggregated with search and smart groups.",
    metaTitle: "k5.ai — InfoSec Security News Feed",
    metaDescription:
      "Real-time security news feed aggregating threat intelligence, vulnerabilities, and cybersecurity updates from trusted sources worldwide.",
    searchPlaceholder: "Search CVE, actor, source...",
    footerText: "k5.ai — Security Intelligence Platform",
    features: { trends: true, morningCall: true, threatActors: true, duplicates: false },
  },
  "4u": {
    id: "4u",
    logoText: { primary: "4u", suffix: ".ai" },
    iconName: "cpu",
    heading: "AI & ML News Feed",
    tagline:
      "Curated AI and machine learning news from public RSS sources, pre-aggregated with search and smart groups.",
    metaTitle: "4u.ai — AI & ML News Feed",
    metaDescription:
      "Real-time news feed aggregating artificial intelligence, machine learning, and data science updates from trusted sources worldwide.",
    searchPlaceholder: "Search title, source...",
    footerText: "4u.ai — AI News Platform",
    features: { trends: false, morningCall: false, threatActors: false, duplicates: false },
  },
  economics: {
    id: "economics",
    logoText: { primary: "economic", suffix: ".4u.ai" },
    iconName: "trending-up",
    heading: "Economic News Feed",
    tagline:
      "Curated economic and market news from public RSS sources, pre-aggregated with search and smart groups.",
    metaTitle: "economic.4u.ai — Economic News Feed",
    metaDescription:
      "Real-time news feed aggregating economic, market, and finance updates from trusted sources worldwide.",
    searchPlaceholder: "Search title, source...",
    footerText: "economic.4u.ai — Economic News Platform",
    features: { trends: false, morningCall: false, threatActors: false, duplicates: false },
  },
  storage: {
    id: "storage",
    logoText: { primary: "storage", suffix: ".4u.ai" },
    iconName: "database",
    heading: "Storage News Feed",
    tagline:
      "Curated storage and infrastructure news from public RSS sources, pre-aggregated with search and smart groups.",
    metaTitle: "storage.4u.ai — Storage News Feed",
    metaDescription:
      "Real-time news feed aggregating data storage, infrastructure, and hardware updates from trusted sources worldwide.",
    searchPlaceholder: "Search title, source...",
    footerText: "storage.4u.ai — Storage News Platform",
    features: { trends: false, morningCall: false, threatActors: false, duplicates: false },
  },
  finnish: {
    id: "finnish",
    logoText: { primary: "fi", suffix: ".4u.ai" },
    iconName: "newspaper",
    heading: "Finnish News Feed",
    tagline:
      "Curated Finnish news from public RSS sources, pre-aggregated with search and smart groups.",
    metaTitle: "fi.4u.ai — Finnish News Feed",
    metaDescription:
      "Real-time news feed aggregating Finnish news, official announcements, and media coverage from public sources.",
    searchPlaceholder: "Search title, source...",
    footerText: "fi.4u.ai — Finnish News Platform",
    features: { trends: false, morningCall: false, threatActors: false, duplicates: true },
  },
};

export function getVertical(id: string | undefined): VerticalConfig {
  return VERTICALS[id as VerticalId] ?? VERTICALS.k5;
}

export const ACTIVE_VERTICAL_ID: VerticalId = getVertical(
  typeof import.meta.env !== "undefined" ? import.meta.env.VITE_VERTICAL : undefined,
).id;

export const vertical: VerticalConfig = VERTICALS[ACTIVE_VERTICAL_ID];
