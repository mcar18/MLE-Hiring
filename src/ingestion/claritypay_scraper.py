"""
Scrape claritypay.com: rotating banner stats, value propositions, partners, and multiple pages.
Banner stats (1900+ Merchants, $1.2B+ Credit Issued, 25% MoM Growth, +91 NPS) are extracted from
visible content only; script/metadata/timestamps are excluded. Optionally sift through multiple
site pages (home, FAQs, contact, etc.) for richer content.
"""
import logging
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.config import (
    CLARITYPAY_BASE_DOMAIN,
    CLARITYPAY_CLEAN_ARTIFACT,
    CLARITYPAY_RAW_ARTIFACT,
    CLARITYPAY_URL,
    SCRAPE_MAX_PAGES,
    SCRAPE_RATE_LIMIT_DELAY_SEC,
    SCRAPE_TIMEOUT_SEC,
    USER_AGENT,
)
from src.utils.io_utils import ensure_dir, save_json

logger = logging.getLogger(__name__)

# Patterns that indicate script/metadata/timestamp — exclude from stat extraction
SCRIPT_NOISE = re.compile(
    r"GMT|Published|function\s*\(|getTime|var\s+\w|\.push\s*\(|event\.|w\[l\]|d\.getTime",
    re.I,
)
# Stat + label patterns for the rotating banner (order matters for first-match)
BANNER_STAT_PATTERNS = [
    ("merchant_count", re.compile(r"([\d,]+\.?\d*[KMB]?\+?)\s*merchants?\w*", re.I)),
    ("credit_issued", re.compile(r"(\$[\d,]+\.?\d*[KMB]?\+?)\s*credit\w*\s*issued?", re.I)),
    ("growth_rate", re.compile(r"(\d+%?)\s*(?:MoM\s*)?(?:customer\s*)?growth\w*", re.I)),
    ("nps_score", re.compile(r"(\+\d+|\d+)\s*(?:net\s*promoter\s*score|nps)", re.I)),
    ("nps_score_alt", re.compile(r"nps[^\d]*(\d+)", re.I)),
]


def _strip_script_style(soup: BeautifulSoup) -> None:
    """Remove script, style, and noscript so their text is not used for stats."""
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()


def _is_noise_text(text: str) -> bool:
    """True if text looks like script, timestamp, or other non–banner content."""
    if not text or len(text) > 500:
        return True
    return bool(SCRIPT_NOISE.search(text))


def _get_visible_text_blocks(soup: BeautifulSoup) -> list[str]:
    """Get visible text as blocks (e.g. div/section text), skipping noise."""
    blocks = []
    for tag in soup.find_all(["div", "section", "span", "p", "h1", "h2", "h3", "li"]):
        t = (tag.get_text() or "").strip()
        if t and not _is_noise_text(t) and len(t) <= 300:
            blocks.append(t)
    return blocks


def _extract_banner_stats_from_text(blocks: list[str]) -> dict[str, str]:
    """
    Extract banner stats (merchant_count, credit_issued, growth_rate, nps_score) from
    visible text that matches known rotating-banner phrases. Prefer regex match, then
    fallback: same block contains both number pattern and keyword.
    """
    result: dict[str, str] = {}
    full_text = " ".join(blocks)

    for key, pattern in BANNER_STAT_PATTERNS:
        if key in result:
            continue
        if key == "nps_score_alt" and "nps_score" in result:
            continue
        for block in blocks + [full_text]:
            m = pattern.search(block)
            if m:
                val = m.group(1).strip()
                if key == "nps_score_alt":
                    result["nps_score"] = val
                else:
                    result[key] = val
                break

    # Fallback: same block has number + keyword (for split DOM / carousel)
    if "merchant_count" not in result:
        for block in blocks:
            if re.search(r"merchants?\w*", block, re.I) and re.search(r"[\d,]+\.?\d*[KMB]?\+?", block):
                m = re.search(r"([\d,]+\.?\d*[KMB]?\+?)", block)
                if m:
                    result["merchant_count"] = m.group(1).strip()
                    break
    if "credit_issued" not in result:
        for block in blocks:
            if re.search(r"credit\w*\s*issued?|issued\s*\$", block, re.I) and re.search(r"\$[\d,]+", block):
                m = re.search(r"(\$[\d,]+\.?\d*[KMB]?\+?)", block)
                if m:
                    result["credit_issued"] = m.group(1).strip()
                    break
    if "growth_rate" not in result:
        for block in blocks:
            if re.search(r"growth|mom", block, re.I) and re.search(r"\d+%?", block):
                m = re.search(r"(\d+%?)", block)
                if m:
                    result["growth_rate"] = m.group(1).strip()
                    break
    if "nps_score" not in result:
        for block in blocks:
            if re.search(r"net\s*promoter|nps", block, re.I) and re.search(r"\+\d+|\d+", block):
                m = re.search(r"(\+\d+|\d+)", block)
                if m:
                    result["nps_score"] = m.group(1).strip()
                    break

    return result


def _extract_public_stats_from_banner(banner_stats: dict[str, str]) -> dict[str, str]:
    """Build public_stats dict for raw output from banner_stats (no script noise)."""
    out = {}
    labels = {
        "merchant_count": "Merchants Served",
        "credit_issued": "Credit Issued",
        "growth_rate": "MoM Customer Growth",
        "nps_score": "Net Promoter Score",
    }
    for k, v in banner_stats.items():
        if v and k in labels:
            out[v] = labels[k]
    return out


def _extract_value_propositions(soup: BeautifulSoup) -> list[str]:
    """Value props from headings and list items; exclude noise."""
    propositions = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = (tag.get_text() or "").strip()
        if not text or _is_noise_text(text) or len(text) > 250:
            continue
        lower = text.lower()
        if any(
            x in lower
            for x in (
                "pay over time",
                "pay-over-time",
                "clear terms",
                "flexible",
                "credit",
                "financing",
                "pre-approval",
                "autopay",
                "support",
                "peace of mind",
            )
        ):
            if text not in propositions:
                propositions.append(text)
    return propositions


def _extract_partners(soup: BeautifulSoup) -> list[str]:
    """Partner names from alt text and 'Proud Partner' context."""
    partners = []
    for tag in soup.find_all(["img", "span", "div"]):
        alt = (tag.get("alt") or "").strip()
        text = (tag.get_text() or "").strip()
        combined = (alt + " " + text).lower()
        if "partner" in combined or ("logo" in alt and len(alt) > 2):
            if alt and alt not in partners:
                partners.append(alt)
            elif text and len(text) < 60 and text not in partners:
                partners.append(text)
    return partners


def _get_same_site_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Collect same-site hrefs (path only, normalized) for multi-page scraping."""
    base_domain = urlparse(base_url).netloc.lower()
    paths = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if parsed.netloc.lower() != base_domain:
            continue
        path = parsed.path.rstrip("/") or "/"
        if path not in paths:
            paths.add(path)
    return sorted(paths)


def _fetch_page(
    url: str,
    headers: dict,
    timeout_sec: int = SCRAPE_TIMEOUT_SEC,
) -> str | None:
    """Fetch one page; return HTML or None on failure."""
    try:
        r = requests.get(url, headers=headers, timeout=timeout_sec)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.warning("Fetch failed %s: %s", url, e)
        return None


def scrape_one_page(
    url: str,
    timeout_sec: int = SCRAPE_TIMEOUT_SEC,
    user_agent: str = USER_AGENT,
) -> dict[str, Any]:
    """
    Scrape a single page: strip script/style, extract banner stats from visible text,
    value propositions, and partners. Returns dict with url, banner_stats, public_stats,
    value_propositions, partners, and same_site_paths (for multi-page).
    """
    headers = {"User-Agent": user_agent}
    html = _fetch_page(url, headers, timeout_sec)
    if not html:
        return {"url": url, "error": "Fetch failed", "banner_stats": {}, "public_stats": {}, "value_propositions": [], "partners": []}

    soup = BeautifulSoup(html, "html.parser")
    _strip_script_style(soup)

    blocks = _get_visible_text_blocks(soup)
    banner_stats = _extract_banner_stats_from_text(blocks)
    public_stats = _extract_public_stats_from_banner(banner_stats)

    value_propositions = _extract_value_propositions(soup)
    partners = _extract_partners(soup)
    same_site_paths = _get_same_site_links(soup, url)

    return {
        "url": url,
        "banner_stats": banner_stats,
        "public_stats": public_stats,
        "value_propositions": value_propositions,
        "partners": partners,
        "same_site_paths": same_site_paths,
    }


def scrape_claritypay(
    base_url: str = CLARITYPAY_URL,
    timeout_sec: int = SCRAPE_TIMEOUT_SEC,
    user_agent: str = USER_AGENT,
    rate_limit_delay_sec: float = SCRAPE_RATE_LIMIT_DELAY_SEC,
    max_pages: int = SCRAPE_MAX_PAGES,
) -> dict[str, Any]:
    """
    Scrape homepage first for banner stats, then discover and scrape other same-site pages.
    Banner stats (1900+ Merchants, $1.2B+ Credit, etc.) are taken from visible content only.
    Returns raw dict with pages, aggregated value_propositions/partners, and banner_stats.
    """
    headers = {"User-Agent": user_agent}
    base_domain = urlparse(base_url).netloc
    base_scheme = urlparse(base_url).scheme or "https"

    # 1) Homepage
    first = scrape_one_page(base_url, timeout_sec, user_agent)
    time.sleep(rate_limit_delay_sec)

    all_value_propositions = list(first.get("value_propositions", []))
    all_partners = list(first.get("partners", []))
    banner_stats = dict(first.get("banner_stats", {}))
    public_stats = dict(first.get("public_stats", {}))
    pages = {"/": first}

    # 2) Discover and scrape other pages (same site)
    to_visit = [
        p for p in first.get("same_site_paths", [])
        if p != "/" and not p.startswith("/#")
    ][: max_pages - 1]
    seen = {"/"}

    for path in to_visit:
        if path in seen or len(pages) >= max_pages:
            continue
        seen.add(path)
        page_url = f"{base_scheme}://{base_domain}{path}"
        time.sleep(rate_limit_delay_sec)
        page_data = scrape_one_page(page_url, timeout_sec, user_agent)
        pages[path] = page_data
        for v in page_data.get("value_propositions", []):
            if v not in all_value_propositions:
                all_value_propositions.append(v)
        for p in page_data.get("partners", []):
            if p not in all_partners:
                all_partners.append(p)
        # If homepage had no banner stats, try this page (e.g. stats on another landing)
        if not banner_stats and page_data.get("banner_stats"):
            banner_stats = dict(page_data["banner_stats"])
            public_stats = dict(page_data.get("public_stats", {}))

    raw = {
        "url": base_url,
        "pages": {path: {k: v for k, v in data.items() if k != "same_site_paths"} for path, data in pages.items()},
        "banner_stats": banner_stats,
        "public_stats": public_stats,
        "value_propositions": all_value_propositions[:25],
        "partners": all_partners[:25],
    }
    return raw


def _clean_scrape_to_meaningful_stats(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Build clean output for the report: banner stats (merchant_count, credit_issued,
    growth_rate, nps_score) plus value_propositions and partners. Uses banner_stats
    from the scraper (no script/timestamp noise).
    """
    banner = raw.get("banner_stats", {})
    clean: dict[str, Any] = {
        "merchant_count": banner.get("merchant_count"),
        "credit_issued": banner.get("credit_issued"),
        "growth_rate": banner.get("growth_rate"),
        "nps_score": banner.get("nps_score"),
        "value_propositions": raw.get("value_propositions", [])[:15],
        "partners": raw.get("partners", [])[:15],
        "pages_scraped": list(raw.get("pages", {}).keys()),
    }
    return clean


def scrape_and_save(
    raw_path: Path = CLARITYPAY_RAW_ARTIFACT,
    clean_path: Path = CLARITYPAY_CLEAN_ARTIFACT,
) -> dict[str, Any]:
    """Scrape ClarityPay (multi-page); save raw and clean. Returns clean dict (used in report)."""
    raw = scrape_claritypay()
    ensure_dir(raw_path)
    save_json(raw, raw_path)
    clean = _clean_scrape_to_meaningful_stats(raw)
    ensure_dir(clean_path)
    save_json(clean, clean_path)
    from src.config import CLARITYPAY_ARTIFACT
    save_json(clean, CLARITYPAY_ARTIFACT)
    logger.info(
        "ClarityPay scrape: banner_stats=%s, pages=%s",
        clean.get("merchant_count") or "—",
        clean.get("pages_scraped", []),
    )
    return clean
