export interface ThreatActorTaxonomy {
  id: string;
  name: string;
  description: string;
  methodology: string;
  examples: string[];
  sources: {
    name: string;
    url: string;
    description: string;
  }[];
  actorPattern: RegExp;
}

export const TAXONOMIES: Record<string, ThreatActorTaxonomy> = {
  "apt": {
    id: "apt",
    name: "APT (Advanced Persistent Threat) Groups",
    description: "Nation-state sponsored threat actors identified by MITRE ATT&CK. APT groups are typically well-resourced, sophisticated actors conducting long-term campaigns for espionage, sabotage, or strategic objectives.",
    methodology: "Numbered sequentially as they are discovered and documented (APT1, APT28, APT29, etc.). The numbering does not indicate sophistication or danger level, only the order of documentation.",
    examples: ["APT1", "APT28", "APT29", "APT41"],
    sources: [
      {
        name: "MITRE ATT&CK Groups",
        url: "https://attack.mitre.org/groups/",
        description: "Comprehensive database of APT groups with TTPs, tools, and campaigns"
      },
      {
        name: "APT Groups and Operations",
        url: "https://docs.google.com/spreadsheets/d/1H9_xaxQHpWaa4O_Son4Gx0YOIzlcBWMsdvePFX68EKU/edit#gid=1864660085",
        description: "Community-maintained spreadsheet tracking APT groups and operations"
      }
    ],
    actorPattern: /^APT[-]?(\d+|C-\d+)$/i
  },

  "fin": {
    id: "fin",
    name: "FIN (Financial Threat) Groups",
    description: "Financially motivated cybercrime groups tracked by FireEye/Mandiant. FIN groups primarily target financial institutions, payment systems, and retail for monetary gain through fraud, theft, or extortion.",
    methodology: "Numbered groups (FIN4, FIN7, FIN8, etc.) tracked by Mandiant based on unique TTPs and infrastructure. Each FIN designation represents a distinct cluster of activity.",
    examples: ["FIN7", "FIN8", "FIN10", "FIN13"],
    sources: [
      {
        name: "Mandiant APT Groups",
        url: "https://www.mandiant.com/resources/insights/apt-groups",
        description: "Mandiant's threat intelligence on FIN and APT groups"
      },
      {
        name: "MITRE ATT&CK - FIN Groups",
        url: "https://attack.mitre.org/groups/?general-filter=FIN",
        description: "MITRE ATT&CK documentation of FIN group TTPs"
      }
    ],
    actorPattern: /^FIN\d+$/i
  },

  "ta": {
    id: "ta",
    name: "TA (Threat Actor) Groups",
    description: "Threat actor clusters identified by Proofpoint and other security researchers. TA groups are typically tracked based on email-based campaigns, malware distribution, and attack infrastructure.",
    methodology: "Numbered threat actor designations (TA505, TA551, TA577, etc.) used primarily by Proofpoint to track distinct threat groups. Numbers help security teams reference specific campaign clusters.",
    examples: ["TA505", "TA551", "TA577", "TA2541"],
    sources: [
      {
        name: "Proofpoint Threat Insight",
        url: "https://www.proofpoint.com/us/threat-insight",
        description: "Proofpoint's threat intelligence and TA group tracking"
      },
      {
        name: "MITRE ATT&CK - TA Groups",
        url: "https://attack.mitre.org/groups/",
        description: "Cross-referenced TA groups in MITRE framework"
      }
    ],
    actorPattern: /^TA\d+$/i
  },

  "microsoft-weather": {
    id: "microsoft-weather",
    name: "Microsoft Weather-Based Taxonomy",
    description: "Microsoft's standardized threat actor naming convention using weather patterns. This system provides consistent, easily recognizable names that indicate both the threat type and origin.",
    methodology: "Element + Weather Pattern format. The element (color/material) indicates origin, while weather type indicates motivation: Typhoon (China), Blizzard (Russia), Sandstorm (Iran), Tempest (Financial), Sleet (North Korea), Tsunami (Others), Storm (Emerging).",
    examples: [
      "Midnight Blizzard (Russia)",
      "Salt Typhoon (China)",
      "Peach Sandstorm (Iran)",
      "Octo Tempest (Financial)",
      "Diamond Sleet (North Korea)"
    ],
    sources: [
      {
        name: "Microsoft Threat Actor Naming",
        url: "https://learn.microsoft.com/en-us/security/intelligence/microsoft-threat-actor-naming",
        description: "Official documentation of Microsoft's naming convention"
      },
      {
        name: "Microsoft Threat Actors Portal",
        url: "https://aka.ms/threatactors",
        description: "Searchable database of Microsoft-tracked threat actors"
      },
      {
        name: "Microsoft Security Blog",
        url: "https://www.microsoft.com/en-us/security/blog/threat-intelligence/",
        description: "Latest threat intelligence reports and analysis"
      }
    ],
    actorPattern: /\s+(Blizzard|Typhoon|Sandstorm|Tempest|Sleet|Tsunami|Rain|Flood|Cyclone|Hail|Lightning|Dust|Squall|Gust)$/i
  },

  "microsoft-storm": {
    id: "microsoft-storm",
    name: "Microsoft Storm Groups",
    description: "Microsoft's designation for emerging or developing threat activity clusters. Storm groups represent newly identified threats that may be merged with existing groups or promoted to full taxonomy names as intelligence matures.",
    methodology: "Storm-XXXX format where the number is a tracking identifier. These are temporary designations used while Microsoft analyzes whether the activity represents a new group or an existing actor's new campaign.",
    examples: ["Storm-0501", "Storm-1811", "Storm-2246"],
    sources: [
      {
        name: "Microsoft Threat Actor Naming",
        url: "https://learn.microsoft.com/en-us/security/intelligence/microsoft-threat-actor-naming",
        description: "Explanation of Storm group designation system"
      },
      {
        name: "Microsoft Security Blog",
        url: "https://www.microsoft.com/en-us/security/blog/threat-intelligence/",
        description: "Storm group activity reports and analysis"
      }
    ],
    actorPattern: /^Storm-\d+$/i
  },

  "crowdstrike-animal": {
    id: "crowdstrike-animal",
    name: "CrowdStrike Animal-Based Taxonomy",
    description: "CrowdStrike's threat actor naming using animals to indicate origin and motivation. This system provides memorable names that security teams can quickly recognize and communicate.",
    methodology: "Adjective + Animal format. Animals indicate origin/motivation: Spider (eCrime), Bear (Russia), Panda (China), Tiger (India), Chollima (North Korea), Kitten (Iran), Jackal (Hacktivist), Ocelot (South America). The adjective differentiates specific groups.",
    examples: [
      "Wizard Spider (eCrime/Ransomware)",
      "Fancy Bear (Russia)",
      "Mustang Panda (China)",
      "Scattered Spider (eCrime)"
    ],
    sources: [
      {
        name: "CrowdStrike Adversary Universe",
        url: "https://adversary.crowdstrike.com/",
        description: "Comprehensive database of CrowdStrike-tracked adversaries"
      },
      {
        name: "CrowdStrike Threat Intelligence",
        url: "https://www.crowdstrike.com/adversaries/",
        description: "Threat actor profiles and intelligence reports"
      },
      {
        name: "CrowdStrike Blog",
        url: "https://www.crowdstrike.com/blog/category/threat-intel-research/",
        description: "Latest research on adversary tactics and campaigns"
      }
    ],
    actorPattern: /\s+(SPIDER|BEAR|PANDA|TIGER|CHOLLIMA|KITTEN|JACKAL|OCELOT)$/i
  },

  "named": {
    id: "named",
    name: "Named Threat Groups",
    description: "Threat actors identified by descriptive names rather than taxonomy codes. These names often reflect the group's operations, tools, or characteristics and may be assigned by multiple security vendors.",
    methodology: "Descriptive names based on observed behavior, tools used, or target profile (e.g., Lazarus Group, Sandworm, Scattered Spider). Names may vary across vendors, with some groups having multiple aliases.",
    examples: [
      "Lazarus Group",
      "Sandworm Team",
      "Scattered Spider",
      "LAPSUS$",
      "Akira"
    ],
    sources: [
      {
        name: "MITRE ATT&CK Groups",
        url: "https://attack.mitre.org/groups/",
        description: "Cross-reference named groups with their aliases and TTPs"
      },
      {
        name: "Threat Actor Map",
        url: "https://aptmap.netlify.app/",
        description: "Visual mapping of threat actors and their relationships"
      }
    ],
    actorPattern: /.*/  // Matches anything not caught by other patterns
  }
};

export function getTaxonomyForActor(actorName: string): ThreatActorTaxonomy {
  // Check each taxonomy pattern
  for (const taxonomy of Object.values(TAXONOMIES)) {
    if (taxonomy.actorPattern.test(actorName)) {
      return taxonomy;
    }
  }

  // Default to named groups
  return TAXONOMIES.named;
}

export function getTaxonomyId(actorName: string): string {
  return getTaxonomyForActor(actorName).id;
}
