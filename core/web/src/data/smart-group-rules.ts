// Declarative smart group rules for economics data
// Only used as a fallback when backend smart_groups are missing/empty.

export type SmartGroup = {
  name: string;
  keywords: (string | RegExp)[];
};

// Existing groups observed in datasets:
// Central Banks, Inflation & Prices, Emerging Markets, Trade & Supply Chains,
// Monetary Policy, Macro & Growth, Energy & Commodities, Markets & Rates,
// Housing & Real Estate, Labor & Wages, Fiscal Policy & Debt, Euro Area, US Economy,
// Financial Stability, Nordics & Finland

export const SMART_GROUP_RULES: SmartGroup[] = [
  {
    name: "Trade & Supply Chains",
    keywords: [
      /supply\s*chain/i,
      /export control/i,
      /\bimport\b|\bexport\b/i,
      /tariff/i,
      /logistic/i,
      /port\b/i,
      /shipment|freight/i,
      /semiconductor|chip\b|foundry|TSMC|ASML|Micron|Intel|Samsung/i,
      /manufactur(e|ing)/i,
      /reshor(e|ing)|nearshor(e|ing)/i,
      /data\s*center/i,
    ],
  },
  {
    name: "Energy & Commodities",
    keywords: [
      /oil\b|Brent|WTI|OPEC/i,
      /gas\b|natural\s*gas/i,
      /lithium|copper|nickel|cobalt|uranium|coal|iron ore/i,
      /battery|refinery|commodity|mining/i,
      /nuclear|reactor/i,
    ],
  },
  {
    name: "Markets & Rates",
    keywords: [
      /treasur(y|ies)|bond|yield\b|spread/i,
      /stock|equit(y|ies)|market|index|Nasdaq|S&P|Dow/i,
      /selloff|rally|volatility/i,
      /rate\b|basis\s*points|\bbps\b/i,
    ],
  },
  {
    name: "Inflation & Prices",
    keywords: [/CPI\b|PPI\b|inflation|deflation|disinflation|price/i],
  },
  {
    name: "Central Banks",
    keywords: [
      /Federal\s*Reserve|\bFed\b/i,
      /European\s*Central\s*Bank|\bECB\b/i,
      /Bank\s*of\s*Japan|\bBOJ\b/i,
      /Bank\s*of\s*England|\bBOE\b/i,
      /PBOC|SNB|RBI|central\s*bank/i,
    ],
  },
  {
    name: "Monetary Policy",
    keywords: [/rate\s*(hike|cut)|policy\s*rate|quantitative|QE|QT|forward\s*guidance/i],
  },
  {
    name: "Housing & Real Estate",
    keywords: [/housing|home\s*price|mortgage|real\s*estate|property/i],
  },
  {
    name: "Labor & Wages",
    keywords: [/job\b|payroll|wage|unemployment|labor|employment|jobless/i],
  },
  {
    name: "Macro & Growth",
    keywords: [/\bGDP\b|growth|recession|expansion|contraction|PMI|industrial\s*production|macro/i],
  },
  {
    name: "Emerging Markets",
    keywords: [
      /India|Malaysia|Thailand|Vietnam|Philippines|Indonesia|Pakistan/i,
      /Brazil|Mexico|Turkey|South\s*Africa|Nigeria|Chile|Peru|Colombia/i,
      /Venezuela|Kazakhstan|Uzbekistan|Central\s*Asia/i,
    ],
  },
  {
    name: "US Economy",
    keywords: [/\bU\.?S\.?\b|United\s*States|America(n)?\b/i],
  },
  {
    name: "Euro Area",
    keywords: [/Euro\s*(area|zone)|Germany|France|Italy|Spain|Portugal|Netherlands/i],
  },
  {
    name: "Fiscal Policy & Debt",
    keywords: [/fiscal|budget|deficit|debt\b|treasury\b|spending|surplus/i],
  },
  {
    name: "Financial Stability",
    keywords: [/bank\s*failure|liquidity\s*crisis|bailout|resolution|contagion/i],
  },
  {
    name: "Nordics & Finland",
    keywords: [/Finland|Sweden|Norway|Denmark|Nordic/i],
  },
];

export function deriveSmartGroupsFromText(
  title: string,
  summary: string,
  source?: string
): string[] {
  const hay = `${title}\n${summary}\n${source ?? ""}`;
  const found = new Set<string>();
  for (const rule of SMART_GROUP_RULES) {
    if (rule.keywords.some((k) => (typeof k === "string" ? new RegExp(k, "i").test(hay) : k.test(hay)))) {
      found.add(rule.name);
    }
  }
  return Array.from(found);
}
