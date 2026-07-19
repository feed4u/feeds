"""
Storage vertical smart group rules.

Extends the default smart groups with storage‑specific topics. Order matters
only for display; matching stops per group once a keyword hits. Keywords are
matched case‑insensitively against title + summary + source.
"""

from __future__ import annotations

from typing import List, Tuple

# Import base smart groups from the ingestion package
try:
    # When running scripts from core/code/base, this import path is available
    from news_fetcher.smart_groups import SMART_GROUP_RULES as BASE_RULES
except Exception:  # pragma: no cover – fallback if import path differs
    BASE_RULES = []  # type: ignore[assignment]


STORAGE_RULES: List[Tuple[str, List[str]]] = [
    (
        "S3 / Object Storage",
        [
            "s3",
            "object storage",
            "s3-compatible",
            "s3 api",
            "bucket policy",
            "s3 bucket",
            "minio",
            "cloudflare r2",
            "r2",
            "backblaze b2",
            "b2",
            "wasabi",
            "digitalocean spaces",
            "spaces",
            "vultr object storage",
            "scality",
            "openstack swift",
            "swift",
            "rgw",
        ],
    ),
    (
        "Ceph / RADOS",
        [
            "ceph",
            "rados",
            "rbd",
            "cephfs",
            "bluestore",
            "crush map",
            "osd",
            "mon",
            "mgr",
            "rook",
        ],
    ),
]


# Exclude some generic security groups not needed for the storage vertical
EXCLUDED_GROUPS = {
    "Vulnerabilities / CVEs",
    "Crypto / Web3",
    "AI/ML Security",
    "Red Team / Offensive",
    "Malware / Payloads",
    "Mobile & App Security",
    "Exploit / PoC",
}

# Prepend storage rules; filter base rules to drop excluded groups
_BASE_FILTERED: List[Tuple[str, List[str]]] = [
    (name, keywords)
    for (name, keywords) in list(BASE_RULES)
    if name not in EXCLUDED_GROUPS
]

SMART_GROUP_RULES: List[Tuple[str, List[str]]] = STORAGE_RULES + _BASE_FILTERED
