#!/usr/bin/env python3
"""
Candidate feed tester for economics sources.

Reads candidate rows from a TSV (default: source/economics/candidates.txt),
and for each with a known homepage URL (url column not 'tbd'), probes:
- robots.txt for referenced sitemaps
- sitemap.xml (and sitemap indexes) for news-like URLs
- homepage <link rel="alternate" type="application/(rss|atom)+xml">
- common RSS paths (/rss, /rss.xml, /feed, /atom.xml, /en/rss, /news/rss)

Outputs a concise JSON report to data/economics/candidates_report.json
with discovered feeds and sample pages to aid manual validation.

Usage:
  python scripts/test_candidates.py \
      --input source/economics/candidates.txt \
      --output data/economics/candidates_report.json \
      --max-per-site 5
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from html import unescape
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover - optional for quick runs without bs4
    BeautifulSoup = None  # type: ignore

try:
    import feedparser  # type: ignore
except Exception:  # pragma: no cover
    feedparser = None  # type: ignore


DEFAULT_UA = (
    "news-core-candidate-tester/0.1 (+https://example.local; contact=dev@local)"
)


@dataclass
class Candidate:
    name: str
    category: str
    region: str
    src_type: str
    lang: str
    url: str  # treated as homepage URL for candidates
    status: str
    notes: str


@dataclass
class DiscoveryResult:
    name: str
    category: str
    region: str
    src_type: str
    lang: str
    homepage: Optional[str]
    status: str
    notes: str
    robots_txt_url: Optional[str]
    sitemaps: List[str]
    sitemap_news_like: List[str]
    sitemap_sample_pages: List[str]
    feed_links: List[str]
    heuristics_tried: List[str]
    heuristics_hits: List[str]
    validated_feeds: List[Dict[str, int]]  # {url, entries}
    errors: List[str]


def read_candidates(path: Path) -> List[Candidate]:
    rows: List[Candidate] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for r in reader:
            if not r or r[0].startswith("#"):
                continue
            # Expected columns: name, category, region, type, lang, url, status, notes
            if len(r) < 8:
                # pad short rows
                r = r + [""] * (8 - len(r))
            rows.append(
                Candidate(
                    name=r[0].strip(),
                    category=r[1].strip(),
                    region=r[2].strip(),
                    src_type=r[3].strip(),
                    lang=r[4].strip() or "en",
                    url=r[5].strip(),
                    status=r[6].strip() or "candidate",
                    notes=r[7].strip(),
                )
            )
    return rows


def get(session: requests.Session, url: str, timeout: int) -> Tuple[Optional[requests.Response], Optional[str]]:
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        return resp, None
    except Exception as e:  # pragma: no cover - network variability
        return None, str(e)


def head(session: requests.Session, url: str, timeout: int) -> Tuple[Optional[requests.Response], Optional[str]]:
    try:
        resp = session.head(url, timeout=timeout, allow_redirects=True)
        return resp, None
    except Exception as e:  # pragma: no cover
        return None, str(e)


def base_origin(home: str) -> Optional[str]:
    try:
        p = urlparse(home)
        if not p.scheme or not p.netloc:
            return None
        return f"{p.scheme}://{p.netloc}"
    except Exception:
        return None


def parse_robots_for_sitemaps(text: str) -> List[str]:
    sitemaps: List[str] = []
    for line in text.splitlines():
        if line.lower().startswith("sitemap:"):
            # Allow formats: "Sitemap: https://example/sitemap.xml" or multiple
            val = line.split(":", 1)[1].strip()
            if val:
                sitemaps.append(val)
    return sitemaps


def extract_feed_links_from_html(html: str, base_url: str) -> List[str]:
    results: List[str] = []
    if BeautifulSoup is None:
        # Simple regex fallback
        for m in re.finditer(
            r"<link[^>]+rel=\"alternate\"[^>]+type=\"(application/(rss|atom)\+xml|application/xml)\"[^>]+href=\"([^\"]+)\"",
            html,
            flags=re.IGNORECASE,
        ):
            href = unescape(m.group(3))
            results.append(urljoin(base_url, href))
        return list(dict.fromkeys(results))

    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("link"):
        rel = (" ".join(link.get("rel", [])) or "").lower()
        typ = (link.get("type") or "").lower()
        href = link.get("href")
        if "alternate" in rel and ("rss" in typ or "atom" in typ or typ == "application/xml") and href:
            results.append(urljoin(base_url, href))
    return list(dict.fromkeys(results))


def is_xml_like(resp: requests.Response) -> bool:
    ctype = resp.headers.get("content-type", "").lower()
    return any(t in ctype for t in ("xml", "rss", "atom"))


def discover_for_candidate(
    cand: Candidate,
    session: requests.Session,
    timeout: int,
    max_per_site: int,
) -> DiscoveryResult:
    homepage = cand.url if cand.url and cand.url.lower() != "tbd" else None
    origin = base_origin(homepage) if homepage else None

    robots_url = f"{origin}/robots.txt" if origin else None
    sitemaps: List[str] = []
    sitemap_news_like: List[str] = []
    sitemap_sample_pages: List[str] = []
    feed_links: List[str] = []
    heuristics_tried: List[str] = []
    heuristics_hits: List[str] = []
    validated_feeds: List[Dict[str, int]] = []
    errors: List[str] = []

    # robots.txt
    if robots_url:
        resp, err = get(session, robots_url, timeout)
        if err:
            errors.append(f"robots.txt fetch error: {err}")
        elif resp is not None and resp.ok:
            sitemaps.extend(parse_robots_for_sitemaps(resp.text))
        else:
            errors.append(f"robots.txt status: {None if resp is None else resp.status_code}")

    # default sitemap.xml
    if origin and (not sitemaps):
        sitemaps.append(f"{origin}/sitemap.xml")

    # fetch sitemaps
    checked_sitemaps: List[str] = []
    for sm in sitemaps[: max_per_site or 5]:
        r, e = get(session, sm, timeout)
        checked_sitemaps.append(sm)
        if e:
            errors.append(f"sitemap fetch error: {sm} -> {e}")
            continue
        if not r or not r.ok or not is_xml_like(r):
            continue
        try:
            from xml.etree import ElementTree as ET

            root = ET.fromstring(r.content)
            tag = root.tag.lower()
            # strip namespace
            if "}" in tag:
                tag = tag.split("}", 1)[1]
            if tag == "sitemapindex":
                for sm_el in root.findall("{*}sitemap"):
                    loc_el = sm_el.find("{*}loc")
                    if loc_el is not None and loc_el.text:
                        loc = loc_el.text.strip()
                        if any(k in loc.lower() for k in ("news", "press", "econom", "stat", "blog")):
                            sitemap_news_like.append(loc)
            elif tag == "urlset":
                for url_el in root.findall("{*}url")[: max_per_site or 5]:
                    loc_el = url_el.find("{*}loc")
                    if loc_el is not None and loc_el.text:
                        sitemap_sample_pages.append(loc_el.text.strip())
        except Exception as ex:  # pragma: no cover
            errors.append(f"sitemap parse error: {sm} -> {ex}")

    # Homepage HTML feed links
    if homepage:
        r, e = get(session, homepage, timeout)
        if e:
            errors.append(f"homepage fetch error: {e}")
        elif r is not None and r.ok:
            try:
                feed_links = extract_feed_links_from_html(r.text, homepage)
            except Exception as ex:  # pragma: no cover
                errors.append(f"feed link parse error: {ex}")

    # Heuristic feed paths
    if origin:
        candidates = [
            "/rss",
            "/rss.xml",
            "/feed",
            "/atom.xml",
            "/en/rss",
            "/en/feed",
            "/news/rss",
            "/news/feed",
            "/press/rss",
            "/press/feed",
        ]
        for path in candidates:
            test_url = urljoin(f"{origin}/", path.lstrip("/"))
            heuristics_tried.append(test_url)
            r, _ = head(session, test_url, timeout)
            if r is not None and (r.ok and is_xml_like(r)):
                heuristics_hits.append(test_url)
            else:
                # Try GET as fallback; some hosts don't implement HEAD correctly
                r2, _ = get(session, test_url, timeout)
                if r2 is not None and r2.ok and is_xml_like(r2):
                    heuristics_hits.append(test_url)

    # Validate feeds if feedparser is available
    candidate_feeds = list(dict.fromkeys(feed_links + heuristics_hits))
    if feedparser and candidate_feeds:
        for fu in candidate_feeds[: max_per_site or 5]:
            try:
                d = feedparser.parse(fu)
                if getattr(d, "bozo", 0) and not d.entries:
                    continue
                validated_feeds.append({"url": fu, "entries": len(d.entries)})
            except Exception:  # pragma: no cover
                continue

    return DiscoveryResult(
        name=cand.name,
        category=cand.category,
        region=cand.region,
        src_type=cand.src_type,
        lang=cand.lang,
        homepage=homepage,
        status=cand.status,
        notes=cand.notes,
        robots_txt_url=robots_url,
        sitemaps=checked_sitemaps,
        sitemap_news_like=sitemap_news_like[: max_per_site or 5],
        sitemap_sample_pages=sitemap_sample_pages[: max_per_site or 5],
        feed_links=feed_links,
        heuristics_tried=heuristics_tried[: max_per_site or 10],
        heuristics_hits=heuristics_hits,
        validated_feeds=validated_feeds,
        errors=errors,
    )


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Probe candidate sources for feeds.")
    p.add_argument(
        "--input",
        default="source/economics/candidates.txt",
        help="TSV file with candidates (name, category, region, type, lang, url, status, notes)",
    )
    p.add_argument(
        "--output",
        default="data/economics/candidates_report.json",
        help="Path to JSON report.",
    )
    p.add_argument("--timeout", type=int, default=12, help="HTTP timeout seconds")
    p.add_argument("--max-per-site", type=int, default=5, help="Limit per-site work")
    p.add_argument("--user-agent", default=DEFAULT_UA, help="HTTP User-Agent header")
    args = p.parse_args(argv)

    in_path = Path(args.input)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    candidates = read_candidates(in_path)

    session = requests.Session()
    session.headers["User-Agent"] = args.user_agent

    results: List[Dict] = []
    for cand in candidates:
        if not cand.url or cand.url.lower() == "tbd":
            results.append(
                asdict(
                    DiscoveryResult(
                        name=cand.name,
                        category=cand.category,
                        region=cand.region,
                        src_type=cand.src_type,
                        lang=cand.lang,
                        homepage=None,
                        status=cand.status,
                        notes=cand.notes,
                        robots_txt_url=None,
                        sitemaps=[],
                        sitemap_news_like=[],
                        sitemap_sample_pages=[],
                        feed_links=[],
                        heuristics_tried=[],
                        heuristics_hits=[],
                        validated_feeds=[],
                        errors=["skipped: homepage url is tbd"],
                    )
                )
            )
            continue

        res = discover_for_candidate(
            cand, session=session, timeout=args.timeout, max_per_site=args.max_per_site
        )
        results.append(asdict(res))
        # brief polite pause
        time.sleep(0.2)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump({"generated_at": int(time.time()), "results": results}, f, ensure_ascii=False, indent=2)

    print(f"Wrote report to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

