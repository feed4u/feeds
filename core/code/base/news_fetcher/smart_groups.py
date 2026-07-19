"""
Smart group classification rules.

This file contains all smart group definitions for automatic content classification.
To add or modify smart groups, simply edit the SMART_GROUP_RULES list below.

Each rule is a tuple of (group_name, [keywords]).
Keywords are matched case-insensitively against title + summary.
"""

from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import List, Optional, Tuple

# Smart group classification rules
# Format: (group_name, [keywords])
SMART_GROUP_RULES: List[Tuple[str, List[str]]] = [
    # Ransomware
    (
        "Ransomware",
        [
            "ransomware",
            "ransom note",
            "double extortion",
            "locker",
            "crypto-locker",
            "ransom demand",
            "ransom gang",
            "extortion",
            "data exfiltration extortion",
            "wizard spider",
            "royal ransomware",
            "fin12",
            "muddled libra",
            "scattered spider",
            "black basta",
            "hellokitty",
            "lockbit",
            "lockbit 3.0",
            "lockbit 2.0",
            "alphv",
            "blackcat",
            "alphv/blackcat",
            "clop",
            "cl0p",
            "clop ransomware",
            "conti",
            "conti leaks",
            "emotet",
            "ryuk",
            "maze",
            "maze cartel",
            "egregor",
            "revil",
            "sodinokibi",
            "darkside",
            "dark side",
            "blackmatter",
            "doppelpaymer",
            "vice society",
            "babuk",
            "netwalker",
            "hive ransomware",
            "royal ransom",
            "play ransomware",
            "playcrypt",
            "phobos ransomware",
            "bianlian",
            "redkite",
            "snatch ransomware",
            "fin7",
            "fin13",
            "lazarus",
            "apt41",
            "leak site",
            "ransom negotiation",
            "ransom portal",
            "ransomware-as-a-service",
            "raas",
            "affiliate program",
            "affiliate ransomware",
        ],
    ),
    # Vulnerabilities / CVEs
    (
        "Vulnerabilities / CVEs",
        [
            "cve-",
            "vulnerability",
            "vulnerabilities",
            "remote code execution",
            "rce",
            "privilege escalation",
            "buffer overflow",
            "out-of-bounds write",
            "sql injection",
            "authentication bypass",
            "zero-day",
            "0day",
        ],
    ),
    # Exploit / PoC
    (
        "Exploit / PoC",
        [
            "exploit released",
            "exploit published",
            "poc released",
            "poc published",
            "proof-of-concept",
            "proof of concept",
            "exploit code",
            "exploit available",
            "weaponized",
            "exploit toolkit",
            "working exploit",
            "public exploit",
            "exploit in the wild",
            "actively exploited",
        ],
    ),
    # Microsoft Ecosystem
    (
        "Windows / Microsoft",
        [
            "windows vulnerability",
            "windows exploit",
            "windows security",
            "windows server",
            "windows 10",
            "windows 11",
            "exchange server",
            "office 365",
            "microsoft 365",
            "azure ad",
            "active directory",
            "ad vulnerability",
            "powershell",
            "ms defender",
            "intune",
            "microsoft patch",
            "windows update",
        ],
    ),
    # Linux Ecosystem
    (
        "Linux / Unix",
        [
            "linux",
            "ubuntu",
            "debian",
            "centos",
            "red hat",
            "rhel",
            "suse",
            "unix",
            "systemd",
            "kernel module",
        ],
    ),
    # Cloud / SaaS
    (
        "Cloud / SaaS",
        [
            "aws",
            "azure",
            "gcp",
            "google cloud",
            "cloudflare",
            "okta",
            "auth0",
            "saas",
            "s3 bucket",
            "cloud misconfiguration",
            "iam role",
            "cloudtrail",
            "kubernetes",
            "k8s",
        ],
    ),
    # Threat Actors / APT
    (
        "Threat Actors / APT",
        [
            " apt ",
            " apt-",
            "apt group",
            "lazarus",
            "sandworm",
            "fin7",
            "apt29",
            "apt28",
            "charming kitten",
            "oilrig",
            "turla",
            "cozy bear",
            "fancy bear",
            "wizard spider",
            "black basta",
            "lockbit",
            "muddled libra",
        ],
    ),
    # Malware / Payloads
    (
        "Malware / Payloads",
        [
            "malware",
            "trojan",
            "backdoor",
            "rootkit",
            "botnet",
            "loader",
            "infostealer",
            "info-stealer",
            "keylogger",
            "rat (remote access trojan)",
            "remote access trojan",
            "wiper",
            "locker",
            "locker malware",
        ],
    ),
    # Web App / API Security
    (
        "Web / API Security",
        [
            "xss",
            "cross-site scripting",
            "csrf",
            "cross-site request forgery",
            "sql injection",
            "sqli",
            "lfi",
            "rfi",
            "directory traversal",
            "api security",
            "graphql",
            "web application firewall",
        ],
    ),
    # Identity / Access
    (
        "Identity / Access",
        [
            "mfa",
            "2fa",
            "passwordless",
            "sso",
            "single sign-on",
            "oauth",
            "saml",
            "openid connect",
            "identity provider",
            "idp",
        ],
    ),
    # Network / OT / ICS
    (
        "Network / OT / ICS",
        [
            "ics",
            "scada",
            "plc",
            "industrial control systems",
            "critical infrastructure",
            "ot security",
            "operational technology",
        ],
    ),
    # Data Breaches / Leaks
    (
        "Data Breaches / Leaks",
        [
            "data breach",
            "data leak",
            "leaked data",
            "database leaked",
            "records exposed",
            "credentials leaked",
            "credential dump",
            "publicly exposed",
            "open database",
        ],
    ),
    # Phishing / Social Engineering
    (
        "Phishing / Social Engineering",
        [
            "phishing",
            "spear-phishing",
            "spear phishing",
            "social engineering",
            "credential harvesting",
            "smishing",
            "vishing",
            "business email compromise",
            "bec attack",
        ],
    ),
    # Crypto / Web3
    (
        "Crypto / Web3",
        [
            "crypto exchange",
            "cryptocurrency",
            "defi",
            "dex",
            "web3",
            "smart contract",
            "solidity",
            "rug pull",
            "bridge exploit",
        ],
    ),
    # Supply-chain / Software
    (
        "Supply Chain / Software",
        [
            "software supply chain",
            "ci/cd pipeline",
            "dependency confusion",
            "typosquatting package",
            "malicious npm package",
            "malicious pypi package",
            "malicious nuget package",
        ],
    ),
    # Mobile & App Security
    (
        "Mobile & App Security",
        [
            "android security",
            "ios security",
            "mobile app",
            "mobile application",
            "apk analysis",
            "ipa analysis",
            "mobile malware",
            "mobile threat",
            "app vulnerability",
            "app security",
            "mobile pentest",
            "mobile penetration",
            "jailbreak",
            "rooting",
            "frida",
            "objection",
        ],
    ),
    # IoT & Embedded Security
    (
        "IoT & Embedded Security",
        [
            "iot security",
            "iot vulnerability",
            "embedded security",
            "embedded system",
            "firmware analysis",
            "firmware vulnerability",
            "hardware security",
            "hardware hacking",
            "chip security",
            "secure boot",
            "router vulnerability",
            "router exploit",
            "smart home",
            "connected device",
        ],
    ),
    # AI/ML Security
    (
        "AI/ML Security",
        [
            "ai security",
            "artificial intelligence security",
            "ml security",
            "machine learning security",
            "llm security",
            "large language model",
            "prompt injection",
            "jailbreak ai",
            "model poisoning",
            "adversarial ai",
            "deepfake",
            "deep fake",
            "chatgpt",
            "gpt-4",
            "claude",
        ],
    ),
    # Privacy & Compliance
    (
        "Privacy & Compliance",
        [
            "gdpr",
            "privacy regulation",
            "data privacy",
            "privacy law",
            "ccpa",
            "hipaa",
            "pci dss",
            "privacy breach",
            "privacy violation",
            "surveillance",
            "tracking",
            "data protection",
            "right to privacy",
            "anonymity",
            "de-anonymization",
        ],
    ),
    # Red Team / Offensive Security
    (
        "Red Team / Offensive",
        [
            "red team",
            "red teaming",
            "penetration test",
            "pentest",
            "offensive security",
            "offensive tool",
            "attack simulation",
            "purple team",
            "breach and attack simulation",
            "adversary simulation",
            "cobalt strike",
            "metasploit",
            "c2 framework",
            "command and control",
        ],
    ),
    # DevSecOps
    (
        "DevSecOps",
        [
            "devsecops",
            "dev sec ops",
            "secure development",
            "secure coding",
            "sast",
            "dast",
            "iast",
            "static analysis",
            "dynamic analysis",
            "security scanning",
            "vulnerability scanner",
            "shift left",
            "security as code",
        ],
    ),
    # Community Discussion
    (
        "Community Discussion",
        [
            "reddit",
            "/r/",
            "discussion",
            "question",
            "asking for advice",
            "career advice",
            "getting started",
            "submitted by /u/",
            "[comments]",
            "[link]",
        ],
    ),
    # Product Announcements
    (
        "Product News",
        [
            "announces",
            "announcing",
            "launches",
            "releases",
            "product update",
            "new version",
            "version release",
            "now available",
            "generally available",
            "coming soon",
            "beta release",
        ],
    ),
]


def get_smart_group_rules(
    vertical: Optional[str] = None, module_path: Optional[Path] = None
) -> List[Tuple[str, List[str]]]:
    """
    Get smart group classification rules.

    Args:
        vertical: Optional vertical identifier that may override the defaults.

    Returns:
        List of (group_name, keywords) tuples
    """
    if module_path and module_path.exists():
        rules = _load_rules_from_path(module_path, vertical or "custom")
        if rules:
            return rules

    if vertical:
        module_names = (
            f"{vertical}.smart_groups",
            f"code.{vertical}.smart_groups",
        )
        for module_name in module_names:
            try:
                module = import_module(module_name)
            except ModuleNotFoundError:
                continue
            rules = getattr(module, "SMART_GROUP_RULES", None)
            if rules:
                return rules

    return SMART_GROUP_RULES


def _load_rules_from_path(path: Path, vertical: str) -> Optional[List[Tuple[str, List[str]]]]:
    spec = spec_from_file_location(f"{vertical}_smart_groups", path)
    if not spec or not spec.loader:
        return None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return getattr(module, "SMART_GROUP_RULES", None)
