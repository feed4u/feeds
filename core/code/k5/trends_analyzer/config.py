"""
Configuration for trends analysis including threat patterns, severity scoring, and MITRE ATT&CK mappings.
"""

from typing import Dict, List, Set, Tuple
from pathlib import Path

# Time windows for analysis
WINDOWS = {
    "24h": 1,
    "7d": 7,
    "30d": 30,
    "90d": 90,
}

# Stopwords for keyword extraction
STOPWORDS: Set[str] = {
    # Generic language stopwords
    "the", "and", "for", "with", "from", "this", "that", "have", "has",
    "into", "over", "under", "about", "your", "you", "are", "was", "were",
    "will", "their", "they", "them", "its", "our", "out", "but", "not",
    "can", "could", "would", "should", "may", "might", "than", "then",
    "after", "before", "more", "less", "also", "just", "via",
    # Generic security terms
    "security", "cyber", "attack", "attacks", "threat", "threats",
    "vulnerability", "vulnerabilities", "report", "reports",
    "blog", "post", "news", "data",
    # Common feed words
    "first", "all", "access", "based", "using", "used", "user", "users",
    "update", "updated", "updates", "detail", "details",
    # Protocol/URL fragments
    "http", "https", "www", "com",
}

# Vendor detection keywords
VENDOR_KEYWORDS: Dict[str, List[str]] = {
    "Microsoft": ["microsoft", "windows", "exchange", "azure", "sharepoint", "active directory"],
    "Cisco": ["cisco", "ios xe", "asa"],
    "Palo Alto": ["palo alto", "pan-os"],
    "Fortinet": ["fortinet", "fortigate"],
    "Cloudflare": ["cloudflare"],
    "Google": ["google", "chrome", "android", "gmail", "workspace"],
    "Apple": ["apple", "macos", "ios", "ipados", "safari"],
    "VMware": ["vmware", "esxi", "vcenter"],
    "Citrix": ["citrix", "netscaler"],
    "Progress": ["progress", "moveit"],
    "Atlassian": ["atlassian", "jira", "confluence"],
    "Amazon": ["aws", "amazon web services", "s3", "ec2"],
    "Oracle": ["oracle", "java"],
    "Adobe": ["adobe"],
    "SonicWall": ["sonicwall"],
    "Ivanti": ["ivanti"],
}

# Attack patterns with severity and MITRE ATT&CK mapping
ATTACK_PATTERNS: Dict[str, Dict[str, any]] = {
    "ransomware": {
        "label": "Ransomware",
        "severity": "critical",
        "keywords": ["ransomware", "ransom", "file encryption", "lockbit", "blackcat"],
        "mitre": ["T1486"],  # Data Encrypted for Impact
        "description": "Ransomware attacks and extortion campaigns"
    },
    "zero_day": {
        "label": "Zero-Day Exploits",
        "severity": "critical",
        "keywords": ["0-day", "zero-day", "zero day", "0day"],
        "mitre": ["T1190"],  # Exploit Public-Facing Application
        "description": "Previously unknown vulnerabilities being exploited"
    },
    "supply_chain": {
        "label": "Supply Chain Attacks",
        "severity": "critical",
        "keywords": ["supply chain", "software supply chain", "dependency"],
        "mitre": ["T1195"],  # Supply Chain Compromise
        "description": "Attacks targeting software supply chains"
    },
    "data_breach": {
        "label": "Data Breaches",
        "severity": "high",
        "keywords": ["data breach", "data leak", "data exposure", "database exposed"],
        "mitre": ["T1567"],  # Exfiltration Over Web Service
        "description": "Confirmed data breaches and leaks"
    },
    "credential_theft": {
        "label": "Credential Theft",
        "severity": "high",
        "keywords": ["credential", "password", "infostealer", "credential stuffing"],
        "mitre": ["T1110", "T1555"],  # Brute Force, Credentials from Password Stores
        "description": "Credential theft and password attacks"
    },
    "phishing": {
        "label": "Phishing Campaigns",
        "severity": "high",
        "keywords": ["phishing", "spearphishing", "business email compromise", "bec"],
        "mitre": ["T1566"],  # Phishing
        "description": "Phishing and social engineering attacks"
    },
    "remote_code_execution": {
        "label": "Remote Code Execution",
        "severity": "critical",
        "keywords": ["rce", "remote code execution", "code execution"],
        "mitre": ["T1190"],  # Exploit Public-Facing Application
        "description": "Remote code execution vulnerabilities"
    },
    "privilege_escalation": {
        "label": "Privilege Escalation",
        "severity": "high",
        "keywords": ["privilege escalation", "escalation of privilege", "local privilege"],
        "mitre": ["T1068"],  # Exploitation for Privilege Escalation
        "description": "Privilege escalation vulnerabilities"
    },
    "malware": {
        "label": "Malware Campaigns",
        "severity": "high",
        "keywords": ["malware", "trojan", "backdoor", "rat"],
        "mitre": ["T1204"],  # User Execution
        "description": "Malware distribution campaigns"
    },
    "ddos": {
        "label": "DDoS Attacks",
        "severity": "medium",
        "keywords": ["ddos", "denial of service", "botnet"],
        "mitre": ["T1498"],  # Network Denial of Service
        "description": "Distributed denial of service attacks"
    },
}

# Attack surface categories
ATTACK_SURFACES: Dict[str, Dict[str, any]] = {
    "cloud": {
        "label": "Cloud Infrastructure",
        "keywords": ["cloud", "aws", "azure", "gcp", "s3", "kubernetes", "docker"],
        "severity_multiplier": 1.2,
    },
    "network": {
        "label": "Network Infrastructure",
        "keywords": ["vpn", "firewall", "router", "switch", "gateway"],
        "severity_multiplier": 1.3,
    },
    "application": {
        "label": "Application Layer",
        "keywords": ["web application", "api", "sql injection", "xss"],
        "severity_multiplier": 1.0,
    },
    "endpoint": {
        "label": "Endpoints & Devices",
        "keywords": ["endpoint", "workstation", "laptop", "mobile"],
        "severity_multiplier": 1.1,
    },
    "identity": {
        "label": "Identity & Access",
        "keywords": ["authentication", "authorization", "sso", "mfa", "identity"],
        "severity_multiplier": 1.4,
    },
}

# CVE severity scoring (CVSS interpretation)
CVE_SEVERITY_RANGES: Dict[str, Tuple[float, float]] = {
    "critical": (9.0, 10.0),
    "high": (7.0, 8.9),
    "medium": (4.0, 6.9),
    "low": (0.1, 3.9),
}

# Risk indicators - patterns that suggest elevated risk
RISK_INDICATORS: List[Dict[str, any]] = [
    {
        "pattern": r"actively exploited|exploitation in the wild|under active attack",
        "weight": 2.0,
        "description": "Active exploitation confirmed"
    },
    {
        "pattern": r"critical|severity: critical|cvss.*?10\.0|cvss.*?9\.[5-9]",
        "weight": 1.8,
        "description": "Critical severity rating"
    },
    {
        "pattern": r"patch.*?unavailable|no fix|unpatched",
        "weight": 1.7,
        "description": "No patch available"
    },
    {
        "pattern": r"widespread|mass exploitation|internet-wide",
        "weight": 1.5,
        "description": "Widespread impact"
    },
    {
        "pattern": r"authentication bypass|unauthenticated",
        "weight": 1.6,
        "description": "Authentication bypass"
    },
]

# Trending velocity thresholds
VELOCITY_THRESHOLDS = {
    "surging": 2.0,      # 100%+ increase
    "rising": 1.5,       # 50%+ increase
    "stable": 0.8,       # -20% to +50%
    "declining": 0.0,    # Below -20%
}


class TrendsConfig:
    """Configuration container for trends analysis"""

    def __init__(self):
        self.windows = WINDOWS
        self.stopwords = STOPWORDS
        self.vendor_keywords = VENDOR_KEYWORDS
        self.attack_patterns = ATTACK_PATTERNS
        self.attack_surfaces = ATTACK_SURFACES
        self.cve_severity_ranges = CVE_SEVERITY_RANGES
        self.risk_indicators = RISK_INDICATORS
        self.velocity_thresholds = VELOCITY_THRESHOLDS

    def get_severity_score(self, severity: str) -> float:
        """Convert severity to numeric score"""
        scores = {
            "critical": 4.0,
            "high": 3.0,
            "medium": 2.0,
            "low": 1.0,
        }
        return scores.get(severity.lower(), 2.0)
