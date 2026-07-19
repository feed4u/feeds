export interface ThreatActorProfile {
  name: string;
  summary: string;
  notableAttacks?: string[];
  uniqueMethods?: string[];
  sources: {
    name: string;
    url: string;
  }[];
}

// Actor-specific profiles with detailed summaries
export const ACTOR_PROFILES: Record<string, ThreatActorProfile> = {
  "Play": {
    name: "Play",
    summary: "Since its first appearance in 2022, Play Ransomware Group has been responsible for several major breaches, including at Microsoft Cuba, the City of Oakland, the Swiss government, and Dallas County. Play installs ransomware on company systems, encrypting data and demanding ransom payments or exfiltrating business data to sell on dark web forums. Some attacks have had international repercussions, impacting hundreds of thousands of customers at once.",
    notableAttacks: [
      "Microsoft Cuba",
      "City of Oakland",
      "Swiss government",
      "Dallas County"
    ],
    uniqueMethods: [
      "Exploits FortiOS vulnerabilities (CVE-2020-12812, CVE-2018-13379) and exposed RDP servers for initial access",
      "Uses intermittent encryption - only encrypts selective parts of files to avoid detection by security systems",
      "Distributes ransomware via Group Policy Objects running as scheduled tasks",
      "Leverages company reputation by offering secrecy to those who pay, while publishing non-payers' data on their Tor blog"
    ],
    sources: [
      {
        name: "CISA Alert - Play Ransomware",
        url: "https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-352a"
      },
      {
        name: "MITRE ATT&CK - Play",
        url: "https://attack.mitre.org/software/S1091/"
      },
      {
        name: "Trend Micro Analysis",
        url: "https://www.trendmicro.com/en_us/research/23/l/play-ransomware-group-using-new-custom-data-exfiltration-tool.html"
      }
    ]
  },

  "Lazarus Group": {
    name: "Lazarus Group",
    summary: "Lazarus Group is a North Korean state-sponsored APT group active since at least 2009. The group is known for high-profile cyber espionage and financially motivated attacks, including the 2014 Sony Pictures hack, the 2016 SWIFT banking system heist of $81 million, and the 2017 WannaCry ransomware attack. Lazarus has evolved to target cryptocurrency exchanges and blockchain infrastructure, stealing billions of dollars to fund North Korean regime operations.",
    notableAttacks: [
      "Sony Pictures Entertainment hack (2014)",
      "SWIFT banking system heist - $81 million (2016)",
      "WannaCry ransomware (2017)",
      "Multiple cryptocurrency exchange hacks (2017-present)",
      "Harmony Protocol - $100 million crypto theft (2022)"
    ],
    uniqueMethods: [
      "Uses custom malware families including FALLCHILL, HOPLIGHT, and AppleJeus",
      "Sophisticated social engineering targeting cryptocurrency and blockchain professionals",
      "Supply chain attacks through trojanized software and fake job offers",
      "Employs extensive infrastructure obfuscation and anti-forensics techniques"
    ],
    sources: [
      {
        name: "MITRE ATT&CK - Lazarus Group",
        url: "https://attack.mitre.org/groups/G0032/"
      },
      {
        name: "CISA North Korea Cyber Threats",
        url: "https://www.cisa.gov/topics/cyber-threats-and-advisories/advanced-persistent-threats/north-korea"
      },
      {
        name: "FBI Alert - AppleJeus Malware",
        url: "https://www.fbi.gov/news/stories/lazarus-group-targets-cryptocurrency-industry"
      }
    ]
  },

  "RTM": {
    name: "RTM",
    summary: "RTM (also known as RTM Banking Trojan) is a Russian-speaking cybercrime group active since at least 2015, primarily targeting remote banking systems and financial institutions across Russia, Ukraine, and neighboring countries. The group uses custom banking malware to intercept and manipulate financial transactions in real-time, stealing credentials and redirecting payments. RTM has evolved its toolkit over the years to evade detection and compromise point-of-sale systems and ATM networks.",
    notableAttacks: [
      "Russian regional banks compromise campaign (2017-2018)",
      "Ukrainian financial institutions targeting (2019)",
      "Eastern European POS system breaches (2020-2021)"
    ],
    uniqueMethods: [
      "Uses fileless malware techniques and DLL injection to avoid detection",
      "Employs custom remote access tools (RATs) designed specifically for banking fraud",
      "Leverages VBScript and JavaScript droppers distributed via phishing emails",
      "Real-time transaction manipulation through web injection attacks"
    ],
    sources: [
      {
        name: "ESET Research - RTM Analysis",
        url: "https://www.welivesecurity.com/2017/03/30/carbon-paper-peering-turlas-second-stage-backdoor/"
      },
      {
        name: "Kaspersky RTM Report",
        url: "https://securelist.com/the-rtm-banking-trojan/88513/"
      },
      {
        name: "MITRE ATT&CK - RTM",
        url: "https://attack.mitre.org/software/S0148/"
      }
    ]
  },

  "Akira": {
    name: "Akira",
    summary: "Akira is a ransomware group that emerged in March 2023, quickly establishing itself as a significant threat to organizations worldwide. The group operates a Ransomware-as-a-Service (RaaS) model and has successfully compromised over 250 organizations across multiple sectors including education, finance, real estate, and manufacturing. Akira is known for double extortion tactics - encrypting data while simultaneously exfiltrating sensitive information to pressure victims into paying ransoms ranging from hundreds of thousands to millions of dollars.",
    notableAttacks: [
      "Stanford University data breach (2023)",
      "Sobeys grocery chain Canada (2023)",
      "Multiple US healthcare systems (2023-2024)",
      "Japanese port authority compromise (2024)"
    ],
    uniqueMethods: [
      "Exploits Cisco ASA VPN vulnerabilities (CVE-2020-3259, CVE-2023-20269) for initial access",
      "Uses hybrid encryption scheme combining RSA and ChaCha20 algorithms",
      "Deploys Linux variant targeting VMware ESXi servers",
      "Terminates running processes and services to maximize encryption coverage",
      "Operates dedicated leak site on Tor to publish victim data"
    ],
    sources: [
      {
        name: "CISA Akira Ransomware Advisory",
        url: "https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-353a"
      },
      {
        name: "FBI Flash - Akira Ransomware",
        url: "https://www.ic3.gov/Media/News/2023/230719.pdf"
      },
      {
        name: "Sophos Akira Analysis",
        url: "https://news.sophos.com/en-us/2023/05/16/akira-ransomware/"
      }
    ]
  },

  "Equation": {
    name: "Equation",
    summary: "Equation Group is one of the most sophisticated APT groups ever documented, believed to be linked to the NSA's Tailored Access Operations (TAO) unit. Active since at least 2001, the group has conducted highly targeted espionage operations against governments, telecommunications, aerospace, energy, and research institutions in over 40 countries. Equation is known for pioneering advanced techniques including firmware-level persistence, hard drive firmware implants, and sophisticated encryption. The group gained widespread attention after the Shadow Brokers leak in 2016-2017 exposed their tools, including EternalBlue which was weaponized in the WannaCry and NotPetya attacks.",
    notableAttacks: [
      "Stuxnet operation collaboration (2010)",
      "Hard drive firmware implants across 30+ countries (2001-2015)",
      "Telecommunications infrastructure compromise in Middle East and Asia",
      "Iranian nuclear facilities espionage (2008-2010)"
    ],
    uniqueMethods: [
      "First known group to implant malware in hard drive firmware (Seagate, Western Digital, Toshiba, Maxtor)",
      "Uses sophisticated modular malware platforms including EquationDrug and GrayFish",
      "Employs custom encryption algorithms and virtual file systems hidden in registry",
      "Leverages zero-day exploits years before public disclosure",
      "CD-ROM infection vector for air-gapped systems"
    ],
    sources: [
      {
        name: "Kaspersky Equation Report",
        url: "https://securelist.com/equation-the-death-star-of-malware-galaxy/68750/"
      },
      {
        name: "The Shadow Brokers Leak Analysis",
        url: "https://www.nytimes.com/2017/11/12/us/nsa-shadow-brokers.html"
      },
      {
        name: "MITRE ATT&CK - Equation",
        url: "https://attack.mitre.org/groups/G0020/"
      }
    ]
  },

  "INC Ransom": {
    name: "INC Ransom",
    summary: "INC Ransom (also known as Lynx Ransom) is a ransomware operation that emerged in 2023, operating under a Ransomware-as-a-Service model. The group has quickly gained notoriety for targeting healthcare, government, and critical infrastructure sectors across the United States and Europe. INC Ransom employs double extortion tactics and has been observed using compromised credentials and unpatched vulnerabilities to gain initial access. The group operates a professional-looking leak site and has demonstrated willingness to negotiate with victims while maintaining aggressive timelines for payment.",
    notableAttacks: [
      "Scottish NHS health board attack (2023)",
      "Multiple US healthcare facilities (2024)",
      "European manufacturing sector targets (2024)",
      "Municipal government systems compromise (2024)"
    ],
    uniqueMethods: [
      "Leverages compromised RDP and VPN credentials for initial access",
      "Uses legitimate remote management tools (AnyDesk, TeamViewer) to maintain persistence",
      "Employs intermittent encryption to accelerate the encryption process",
      "Exfiltrates data using cloud storage services and file-sharing platforms",
      "Publishes partial victim data as proof before full leak to pressure payment"
    ],
    sources: [
      {
        name: "CISA INC Ransom Alert",
        url: "https://www.cisa.gov/news-events/cybersecurity-advisories"
      },
      {
        name: "Trend Micro INC Ransom Analysis",
        url: "https://www.trendmicro.com/vinfo/us/security/news/ransomware-spotlight/ransomware-spotlight-inc-ransom"
      },
      {
        name: "Health-ISAC Advisory",
        url: "https://h-isac.org/hisac-intelligence-reports/"
      }
    ]
  },

  "Contagious Interview": {
    name: "Contagious Interview",
    summary: "Contagious Interview (also tracked as DeceptiveDevelopment and VMConnect) is a North Korean state-sponsored social engineering campaign active since 2023, primarily targeting software developers and IT professionals in the cryptocurrency and blockchain sectors. The campaign uses elaborate fake job interview scenarios to deliver malware, with threat actors posing as recruiters from legitimate companies. Victims are lured into downloading malicious coding challenges or development tools that deploy sophisticated backdoors. This operation is believed to be linked to the Lazarus Group infrastructure and serves both espionage and financial theft objectives.",
    notableAttacks: [
      "Cryptocurrency developers targeted across US and Europe (2023-2024)",
      "Blockchain startup compromise via fake interviews (2024)",
      "Open source software maintainers targeted (2024)"
    ],
    uniqueMethods: [
      "Sophisticated social engineering using fake LinkedIn recruiter profiles and websites",
      "Malicious npm packages disguised as coding challenges or interview assignments",
      "Multi-stage infection using BeaverTail malware and InvisibleFerret backdoor",
      "Targets developers on macOS, Windows, and Linux platforms",
      "Steals cryptocurrency wallets, credentials, and source code during fake technical interviews",
      "Uses legitimate video conferencing for initial contact to build trust"
    ],
    sources: [
      {
        name: "Palo Alto Unit 42 - Contagious Interview",
        url: "https://unit42.paloaltonetworks.com/contagious-interview-campaign/"
      },
      {
        name: "CISA North Korea Alert",
        url: "https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-347a"
      },
      {
        name: "CrowdStrike Analysis",
        url: "https://www.crowdstrike.com/blog/targeted-attack-on-software-developers/"
      }
    ]
  },

  "Salt Typhoon": {
    name: "Salt Typhoon",
    summary: "Salt Typhoon is a Chinese state-sponsored APT group identified by Microsoft as part of their weather-based naming taxonomy (Typhoon indicates Chinese origin). Active since at least 2020, Salt Typhoon focuses on cyber espionage operations targeting telecommunications, technology, and government sectors primarily in Southeast Asia and the United States. The group is known for sophisticated network infiltration, long-term persistence, and extensive reconnaissance of telecommunications infrastructure, likely in support of intelligence collection and potential pre-positioning for future operations.",
    notableAttacks: [
      "US telecommunications providers compromise (2024)",
      "Southeast Asian government networks infiltration (2023-2024)",
      "Major ISP infrastructure reconnaissance (2024)"
    ],
    uniqueMethods: [
      "Exploits edge networking devices and security appliances for initial access",
      "Uses living-off-the-land binaries (LOLBins) and legitimate admin tools to avoid detection",
      "Maintains long-term persistence through web shells on internet-facing servers",
      "Focuses on compromising network management systems and lawful intercept infrastructure",
      "Employs advanced tradecraft to hide in legitimate network traffic"
    ],
    sources: [
      {
        name: "Microsoft Threat Intelligence - Salt Typhoon",
        url: "https://www.microsoft.com/en-us/security/blog/threat-intelligence/"
      },
      {
        name: "CISA Chinese APT Activity",
        url: "https://www.cisa.gov/topics/cyber-threats-and-advisories/advanced-persistent-threats/china"
      },
      {
        name: "NSA/FBI Joint Advisory",
        url: "https://media.defense.gov/2024/Feb/07/2003391428/-1/-1/0/JOINT_CSA_PRC_LINKED_ACTORS_COMPROMISE_US_CRITICAL_INFRASTRUCTURE.PDF"
      }
    ]
  },

  "Inception": {
    name: "Inception",
    summary: "Inception (also known as Cloud Atlas and Oxygen) is a sophisticated APT group active since at least 2014, primarily targeting diplomatic, government, and military organizations across Europe, Russia, Central Asia, and the Middle East. The group conducts cyber espionage operations with a focus on geopolitical intelligence collection. Inception is known for its modular malware framework, creative social engineering tactics, and ability to adapt tradecraft to evade detection. The group has demonstrated sustained interest in former Soviet states and countries involved in regional conflicts.",
    notableAttacks: [
      "Russian government entities targeting (2014-2020)",
      "Eastern European diplomatic missions compromise (2017-2019)",
      "Central Asian government networks infiltration (2020-2023)",
      "Defense contractors espionage (2021-2024)"
    ],
    uniqueMethods: [
      "Uses spearphishing with malicious documents exploiting Office vulnerabilities",
      "Deploys modular PowerShell-based malware with plugin architecture",
      "Creates custom browser-based information stealers for data exfiltration",
      "Employs red teaming techniques including USB-borne malware for air-gapped networks",
      "Uses cloud storage services (Google Drive, Dropbox) for C2 communications"
    ],
    sources: [
      {
        name: "Kaspersky Cloud Atlas Report",
        url: "https://securelist.com/recent-cloud-atlas-activity/92016/"
      },
      {
        name: "MITRE ATT&CK - Inception",
        url: "https://attack.mitre.org/groups/G0100/"
      },
      {
        name: "Palo Alto Unit 42 Analysis",
        url: "https://unit42.paloaltonetworks.com/unit42-inception-framework-hiding-behind-proxies/"
      }
    ]
  },

  "Patchwork": {
    name: "Patchwork",
    summary: "Patchwork (also known as Dropping Elephant, Chinastrats, and Monsoon) is a suspected Indian state-sponsored APT group active since at least 2015, primarily conducting cyber espionage against military, diplomatic, and economic targets in Pakistan, China, and other South Asian countries. The group is characterized by relatively unsophisticated but effective techniques, heavy reliance on social engineering, and consistent targeting of individuals involved in South Asian regional affairs. Patchwork has evolved its toolkit over time but maintains focus on document theft and intelligence gathering.",
    notableAttacks: [
      "Pakistani military and diplomatic personnel targeting (2016-2023)",
      "Chinese minority groups and think tanks compromise (2017-2020)",
      "US-based South Asian organizations infiltration (2021-2024)",
      "Bangladesh government entities espionage (2022-2023)"
    ],
    uniqueMethods: [
      "Extensive use of malicious RTF documents exploiting EPS vulnerabilities",
      "Spearphishing emails with romantic themes or fake diplomatic documents",
      "Custom RATs including BADNEWS, PATCHWORK, and QUARKBANDIT",
      "Watering hole attacks on South Asian news and cultural websites",
      "AutoIt-based malware droppers for multi-stage infections",
      "Steals documents, credentials, and screenshots from compromised systems"
    ],
    sources: [
      {
        name: "MITRE ATT&CK - Patchwork",
        url: "https://attack.mitre.org/groups/G0040/"
      },
      {
        name: "Trend Micro Patchwork Analysis",
        url: "https://www.trendmicro.com/en_us/research/17/c/patchwork-cyberespionage-group-expands-targets-from-governments-to-wide-range-of-industries.html"
      },
      {
        name: "Cisco Talos Intelligence",
        url: "https://blog.talosintelligence.com/2018/07/multiple-cobalt-personality-disorder.html"
      }
    ]
  },

  "Storm-0249": {
    name: "Storm-0249",
    summary: "Storm-0249 is a Microsoft-designated emerging threat activity cluster first identified in 2023. The Storm designation indicates that this is developing or newly identified threat activity that Microsoft is still analyzing to determine if it represents a new group or belongs to an existing known actor. Storm-0249 has been observed conducting financially motivated attacks targeting organizations through business email compromise (BEC), phishing campaigns, and subsequent ransomware deployment. The group shows characteristics suggesting possible connection to Nigerian cybercrime ecosystems but with more sophisticated technical capabilities.",
    notableAttacks: [
      "Business email compromise targeting Fortune 500 companies (2023-2024)",
      "Financial sector phishing campaigns (2024)",
      "Law firms and professional services targeting (2024)"
    ],
    uniqueMethods: [
      "Advanced BEC techniques combining social engineering with technical compromise",
      "Uses legitimate cloud services and SaaS platforms to host phishing infrastructure",
      "Employs adversary-in-the-middle (AitM) phishing to bypass MFA",
      "Leverages compromised Microsoft 365 accounts for lateral movement",
      "Combines BEC with ransomware deployment for maximum financial impact"
    ],
    sources: [
      {
        name: "Microsoft Threat Intelligence",
        url: "https://www.microsoft.com/en-us/security/blog/threat-intelligence/"
      },
      {
        name: "Microsoft Defender Threat Analytics",
        url: "https://learn.microsoft.com/en-us/security/intelligence/microsoft-threat-actor-naming"
      },
      {
        name: "Microsoft Security Response",
        url: "https://aka.ms/threatactors"
      }
    ]
  },

  "Rocke": {
    name: "Rocke",
    summary: "Rocke is a Chinese-speaking cybercrime group active since at least 2018, specializing in cryptojacking operations that hijack cloud infrastructure and servers to mine cryptocurrency (primarily Monero). The group is known for aggressive scanning and exploitation of vulnerabilities in web applications, cloud services, and container environments. Rocke has demonstrated sophisticated understanding of cloud-native technologies, Docker, Kubernetes, and Linux systems, using both known exploits and custom malware to maintain persistence and maximize mining operations across compromised infrastructure.",
    notableAttacks: [
      "Mass exploitation of Apache Struts vulnerabilities for cryptomining (2018)",
      "Docker Hub malicious image campaign (2019)",
      "Confluence and WebLogic server compromises (2019-2020)",
      "Jenkins and Hadoop cluster targeting (2020-2021)",
      "Cloud storage bucket hijacking for mining resources (2021-2022)"
    ],
    uniqueMethods: [
      "Deploys XMRig cryptocurrency miner with rootkit capabilities for stealth",
      "Uses GitHub and Pastebin for malware distribution and C2 communications",
      "Exploits misconfigured Docker APIs and Kubernetes dashboards",
      "Implements worm-like propagation to spread across networks automatically",
      "Disables competing miners and security tools on compromised systems",
      "Uses process injection and memory-resident techniques to evade detection"
    ],
    sources: [
      {
        name: "Cisco Talos Rocke Analysis",
        url: "https://blog.talosintelligence.com/2018/08/rocke-champion-of-monero-miners.html"
      },
      {
        name: "Palo Alto Unit 42 - Rocke Evolution",
        url: "https://unit42.paloaltonetworks.com/malware-used-by-rocke-group/"
      },
      {
        name: "Anomali Rocke Infrastructure",
        url: "https://www.anomali.com/blog/rocke-evolves-its-arsenal-with-a-new-malware-family-written-in-golang"
      }
    ]
  },

  "Silence": {
    name: "Silence",
    summary: "Silence is a Russian-speaking financially motivated cybercrime group active since 2016, primarily targeting banks and financial institutions across Russia, Eastern Europe, and Central Asia. The group is notable for using tactics, techniques, and procedures (TTPs) similar to those of the Carbanak APT group, leading some researchers to believe there may be shared toolkits or personnel. Silence conducts sophisticated attacks against banking infrastructure, targeting card processing systems, SWIFT networks, and ATM networks to steal millions of dollars. The group demonstrates deep understanding of banking operations and internal systems.",
    notableAttacks: [
      "Russian banks theft totaling over $4.2 million (2016-2019)",
      "Armenian bank ATM cash-out operation - $800,000 (2018)",
      "Bulgarian bank card processing system compromise (2019)",
      "Kyrgyzstan financial institution SWIFT attack (2019)",
      "Chilean banks targeting via money mule networks (2019-2020)"
    ],
    uniqueMethods: [
      "Uses spearphishing emails with malicious CHM (Compiled HTML Help) attachments",
      "Deploys custom backdoor called 'Silence' with advanced keylogging and screen capture",
      "Leverages Sysinternals and PowerShell Empire for post-exploitation",
      "Creates fraudulent transactions through compromised banking software",
      "Coordinates ATM cash-out operations with money mule networks",
      "Uses video recording of bank employee screens to understand internal processes"
    ],
    sources: [
      {
        name: "Group-IB Silence Report",
        url: "https://www.group-ib.com/resources/threat-research/silence_moving-into-the-darkside.pdf"
      },
      {
        name: "MITRE ATT&CK - Silence",
        url: "https://attack.mitre.org/groups/G0091/"
      },
      {
        name: "Kaspersky Silence Analysis",
        url: "https://securelist.com/the-silence/83009/"
      }
    ]
  },

  "MuddyWater": {
    name: "MuddyWater",
    summary: "MuddyWater (also known as Mango Sandstorm, Static Kitten, and TEMP.Zagros) is an Iranian state-sponsored APT group attributed to Iran's Ministry of Intelligence and Security (MOIS). Active since at least 2017, the group conducts cyber espionage operations targeting government agencies, telecommunications, defense contractors, and critical infrastructure across the Middle East, Europe, Asia, and North America. MuddyWater is characterized by persistent targeting, use of living-off-the-land techniques, and continuous evolution of tactics to evade detection. The group supports broader Iranian intelligence objectives and has been linked to destructive attacks.",
    notableAttacks: [
      "Middle Eastern government ministries espionage (2017-2023)",
      "Turkish defense contractors targeting (2019-2020)",
      "Saudi Arabian telecommunications infrastructure (2020)",
      "Israeli organizations multi-wave campaigns (2021-2023)",
      "US and European critical infrastructure reconnaissance (2022-2024)"
    ],
    uniqueMethods: [
      "Extensive use of PowerShell scripts and macro-enabled documents for initial access",
      "Living-off-the-land binaries (LOLBins) including certutil, regsvr32, and mshta",
      "Custom backdoors including PowGoop, Canopy, and POWERSTATS",
      "DNS tunneling for C2 communications to evade detection",
      "Compromises legitimate websites for watering hole attacks",
      "Uses GitHub, Telegram, and cloud services for command and control",
      "Frequently changes infrastructure and employs anti-analysis techniques"
    ],
    sources: [
      {
        name: "CISA Iranian APT - MuddyWater",
        url: "https://www.cisa.gov/news-events/cybersecurity-advisories/aa22-055a"
      },
      {
        name: "Microsoft Threat Intelligence - Mango Sandstorm",
        url: "https://www.microsoft.com/en-us/security/blog/2022/01/15/destructive-malware-targeting-ukrainian-organizations/"
      },
      {
        name: "MITRE ATT&CK - MuddyWater",
        url: "https://attack.mitre.org/groups/G0069/"
      }
    ]
  }
};

// Check if we have a profile for a specific actor
export function getActorProfile(actorName: string): ThreatActorProfile | null {
  return ACTOR_PROFILES[actorName] || null;
}
