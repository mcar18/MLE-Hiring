"""
Scrape claritypay.com: full-site crawl by stepping through every discovered page,
rotating banner stats, value propositions, partners. Banner stats (including for-business
stats like 85% True Approvals, 250% conversion lift) are merged from all pages.
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
    CLARITYPAY_CLEAN_ARTIFACT,
    CLARITYPAY_RAW_ARTIFACT,
    CLARITYPAY_URL,
    SCRAPE_MAX_PAGES,
    SCRAPE_RATE_LIMIT_DELAY_SEC,
    SCRAPE_RESEARCH_PEOPLE,
    SCRAPE_TIMEOUT_SEC,
    USER_AGENT,
)
from src.utils.io_utils import ensure_dir, save_json

logger = logging.getLogger(__name__)

SCRIPT_NOISE = re.compile(
    r"GMT|Published|function\s*\(|getTime|var\s+\w|\.push\s*\(|event\.|w\[l\]|d\.getTime",
    re.I,
)
# Banner + for-business stats (order matters for first-match)
# growth_rate: require % so we don't capture "8" from "8AM" or similar
BANNER_STAT_PATTERNS = [
    ("merchant_count", re.compile(r"([\d,]+\.?\d*[KMB]?\+?)\s*merchants?\w*", re.I)),
    ("credit_issued", re.compile(r"(\$[\d,]+\.?\d*[KMB]?\+?)\s*credit\w*\s*issued?", re.I)),
    ("growth_rate", re.compile(r"(\d+%)\s*(?:MoM\s*)?(?:customer\s*)?growth\w*", re.I)),  # require % to avoid capturing "8" from time
    ("nps_score", re.compile(r"(\+\d+|\d+)\s*(?:net\s*promoter\s*score|nps)", re.I)),
    ("nps_score_alt", re.compile(r"nps[^\d]*(\d+)", re.I)),
    ("true_approvals_pct", re.compile(r"(\d+%?)\s*true\s*approvals?", re.I)),
    ("conversion_lift_pct", re.compile(r"(\d+%?)\s*(?:increase\s*in\s*)?conversion\s*(?:rate|lift)?", re.I)),
    ("avg_sale_lift_pct", re.compile(r"(\d+%?)\s*(?:higher\s*)?(?:average\s*)?sale\s*(?:amount|lift)?", re.I)),
]


def _strip_script_style(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()


def _is_noise_text(text: str) -> bool:
    if not text or len(text) > 500:
        return True
    return bool(SCRIPT_NOISE.search(text))


def _get_visible_text_blocks(soup: BeautifulSoup) -> list[str]:
    blocks = []
    for tag in soup.find_all(["div", "section", "span", "p", "h1", "h2", "h3", "h4", "li"]):
        t = (tag.get_text() or "").strip()
        if t and not _is_noise_text(t) and len(t) <= 400:
            blocks.append(t)
    return blocks


def _extract_banner_stats_from_text(blocks: list[str]) -> dict[str, str]:
    """Extract all known stats (banner + for-business) from visible text."""
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

    # Fallbacks for banner stats
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
            if re.search(r"growth|mom", block, re.I):
                # Prefer percentage (e.g. 25%) to avoid capturing "8" from "8AM"
                m = re.search(r"(\d+%)", block)
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
    # For-business fallbacks
    if "true_approvals_pct" not in result:
        for block in blocks:
            if "true approval" in block.lower() and re.search(r"\d+%?", block):
                m = re.search(r"(\d+%?)", block)
                if m:
                    result["true_approvals_pct"] = m.group(1).strip()
                    break
    if "conversion_lift_pct" not in result:
        for block in blocks:
            if "conversion" in block.lower() and re.search(r"\d+%?", block):
                m = re.search(r"(\d+%?)", block)
                if m:
                    result["conversion_lift_pct"] = m.group(1).strip()
                    break
    if "avg_sale_lift_pct" not in result:
        for block in blocks:
            if "sale" in block.lower() and "higher" in block.lower() and re.search(r"\d+%?", block):
                m = re.search(r"(\d+%?)", block)
                if m:
                    result["avg_sale_lift_pct"] = m.group(1).strip()
                    break

    return result


def _extract_public_stats_from_banner(banner_stats: dict[str, str]) -> dict[str, str]:
    labels = {
        "merchant_count": "Merchants Served",
        "credit_issued": "Credit Issued",
        "growth_rate": "MoM Customer Growth",
        "nps_score": "Net Promoter Score",
        "true_approvals_pct": "True Approvals",
        "conversion_lift_pct": "Conversion Rate Lift",
        "avg_sale_lift_pct": "Higher Average Sale",
    }
    return {v: banner_stats[k] for k, v in labels.items() if banner_stats.get(k)}


def _extract_value_propositions(soup: BeautifulSoup) -> list[str]:
    propositions = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = (tag.get_text() or "").strip()
        if not text or _is_noise_text(text) or len(text) > 400:
            continue
        lower = text.lower()
        if any(
            x in lower
            for x in (
                "pay over time", "pay-over-time", "clear terms", "flexible", "credit",
                "financing", "pre-approval", "autopay", "support", "peace of mind",
                "approval", "conversion", "sale", "omnichannel", "brand", "loyalty",
            )
        ):
            if text not in propositions:
                propositions.append(text)
    return propositions


def _extract_partners(soup: BeautifulSoup) -> list[str]:
    partners = []
    for tag in soup.find_all(["img", "span", "div"]):
        alt = (tag.get("alt") or "").strip()
        text = (tag.get_text() or "").strip()
        combined = (alt + " " + text).lower()
        if "partner" in combined or ("logo" in alt and len(alt) > 2):
            if alt and alt not in partners:
                partners.append(alt)
            elif text and len(text) < 80 and text not in partners:
                partners.append(text)
    return partners


def _extract_trust_badges_and_logos(soup: BeautifulSoup) -> list[str]:
    """Capture logo/badge text: all img alt text plus any text with BBB, approved, accredited, etc."""
    badges = []
    for tag in soup.find_all("img", alt=True):
        alt = (tag.get("alt") or "").strip()
        if alt and len(alt) < 120 and alt not in badges:
            badges.append(alt)
    trust_keywords = re.compile(r"bbb|approved|accredited|rating|trust|a\+|certified", re.I)
    for tag in soup.find_all(["span", "div", "p", "a"]):
        text = (tag.get_text() or "").strip()
        if text and len(text) < 100 and trust_keywords.search(text) and text not in badges:
            badges.append(text)
    return badges


def _extract_job_listings(soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
    """Extract job listings from careers page (links and headings that look like job titles)."""
    jobs = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = (a.get_text() or "").strip()
        if not text or len(text) > 150:
            continue
        full_url = urljoin(base_url, href)
        if "career" in href.lower() or "job" in href.lower() or "role" in href.lower() or "position" in href.lower():
            jobs.append({"title": text or "Job", "url": full_url})
        if re.search(r"engineer|developer|manager|analyst|director|specialist|coordinator|designer", text, re.I):
            if not any(j.get("title") == text for j in jobs):
                jobs.append({"title": text, "url": full_url})
    for tag in soup.find_all(["h2", "h3", "h4"]):
        text = (tag.get_text() or "").strip()
        if not text or len(text) > 100:
            continue
        if re.search(r"engineer|developer|manager|analyst|director|specialist|coordinator|designer|associate", text, re.I):
            url = ""
            parent = tag.find_parent("a")
            if parent and parent.get("href"):
                url = urljoin(base_url, parent["href"])
            if not any(j.get("title") == text for j in jobs):
                jobs.append({"title": text, "url": url})
    return jobs


def _extract_team_from_about(soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
    """Extract people from about-us: name (headings) and title/LinkedIn from links between this and next heading."""
    people = []
    headings = soup.find_all(["h3", "h4"])
    all_names = {(h.get_text() or "").strip() for h in headings}
    seen_names = set()

    for i, h in enumerate(headings):
        name = (h.get_text() or "").strip()
        if not name or len(name) > 80:
            continue
        if name.lower() in ("leadership", "investors & advisors", "meet the leadership", "our values", "follow us on linkedin"):
            continue
        if len(name.split()) > 5:
            continue
        if name in seen_names:
            continue
        seen_names.add(name)
        title = ""
        linkedin_url = ""
        stop = headings[i + 1] if i + 1 < len(headings) else None
        for tag in h.find_all_next("a", href=True):
            if stop and tag.find_previous(["h3", "h4"]) == stop:
                break
            link_text = (tag.get_text() or "").strip()
            href = tag.get("href", "")
            # If link text is "NextPersonNameTitle" (e.g. "Callie EstreicherChief of Staff"), use "Title" only and don't use this link's URL for LinkedIn
            other_name_prefix = next((other for other in all_names if other != name and (link_text == other or link_text.startswith(other))), None)
            if other_name_prefix:
                suffix = link_text[len(other_name_prefix):].strip()
                if suffix and len(suffix) < 80 and not title and "linkedin" not in suffix.lower():
                    title = suffix
                continue
            if "linkedin.com" in href:
                linkedin_url = urljoin(base_url, href)
                if link_text and len(link_text) < 80 and not title and "linkedin" not in link_text.lower():
                    title = link_text
            elif link_text and len(link_text) < 80 and not title and "linkedin" not in link_text.lower():
                title = link_text
        people.append({"name": name, "title": title or "", "linkedin_url": linkedin_url or ""})
    return people


def _research_person(name: str, title: str, max_results: int = 3) -> dict[str, Any]:
    """Optional: search for person and return search URL + first few result links (duckduckgo_search)."""
    query = f"{name} {title} ClarityPay".strip()
    search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
    out = {"name": name, "title": title, "search_url": search_url, "results": []}
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                out["results"].append({"title": r.get("title", ""), "url": r.get("href", ""), "snippet": (r.get("body") or "")[:200]})
    except Exception as e:
        logger.debug("DuckDuckGo search skipped for %s: %s", name, e)
    return out


def _get_same_site_links(soup: BeautifulSoup, base_url: str) -> list[str]:
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
        # Normalize: strip fragment for dedup
        path = path.split("#")[0].rstrip("/") or "/"
        paths.add(path)
    return sorted(paths)


def _fetch_page(url: str, headers: dict, timeout_sec: int = SCRAPE_TIMEOUT_SEC) -> str | None:
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
    path: str = "",
) -> dict[str, Any]:
    """Scrape a single page; return banner_stats, value_propositions, partners, trust_badges, optional job_listings/team."""
    headers = {"User-Agent": user_agent}
    html = _fetch_page(url, headers, timeout_sec)
    if not html:
        return {"url": url, "error": "Fetch failed", "banner_stats": {}, "public_stats": {}, "value_propositions": [], "partners": [], "trust_badges": [], "same_site_paths": []}

    soup = BeautifulSoup(html, "html.parser")
    _strip_script_style(soup)

    blocks = _get_visible_text_blocks(soup)
    banner_stats = _extract_banner_stats_from_text(blocks)
    public_stats = _extract_public_stats_from_banner(banner_stats)

    value_propositions = _extract_value_propositions(soup)
    partners = _extract_partners(soup)
    trust_badges = _extract_trust_badges_and_logos(soup)
    same_site_paths = _get_same_site_links(soup, url)

    out = {
        "url": url,
        "banner_stats": banner_stats,
        "public_stats": public_stats,
        "value_propositions": value_propositions,
        "partners": partners,
        "trust_badges": trust_badges,
        "same_site_paths": same_site_paths,
    }
    path_lower = (path or url).lower()
    if "career" in path_lower:
        out["job_listings"] = _extract_job_listings(soup, url)
    if "about" in path_lower:
        out["team"] = _extract_team_from_about(soup, url)
    return out


def scrape_claritypay(
    base_url: str = CLARITYPAY_URL,
    timeout_sec: int = SCRAPE_TIMEOUT_SEC,
    user_agent: str = USER_AGENT,
    rate_limit_delay_sec: float = SCRAPE_RATE_LIMIT_DELAY_SEC,
    max_pages: int = SCRAPE_MAX_PAGES,
) -> dict[str, Any]:
    """
    Full-site crawl: start from homepage, discover links from every page, and step through
    each unique same-site page. Merge banner_stats from every page (so for-business stats
    like 85% True Approvals are captured). Aggregate all value_propositions and partners.
    max_pages: 0 = no cap (crawl until no new links); else cap at that number.
    """
    base_domain = urlparse(base_url).netloc
    base_scheme = urlparse(base_url).scheme or "https"
    no_cap = max_pages == 0
    cap = max_pages if not no_cap else 9999

    all_value_propositions: list[str] = []
    all_partners: list[str] = []
    all_trust_badges: list[str] = []
    merged_banner_stats: dict[str, str] = {}
    merged_public_stats: dict[str, str] = {}
    pages: dict[str, dict] = {}
    job_listings: list[dict[str, str]] = []
    team: list[dict[str, str]] = []

    queue: list[str] = ["/"]
    visited: set[str] = set()

    while queue and len(visited) < cap:
        path = queue.pop(0)
        if path in visited:
            continue
        visited.add(path)
        page_url = f"{base_scheme}://{base_domain}{path}" if path != "/" else base_url
        logger.info("Scraping page %s (%d queued, %d visited)", path, len(queue), len(visited))

        time.sleep(rate_limit_delay_sec)
        page_data = scrape_one_page(page_url, timeout_sec, user_agent, path=path)
        pages[path] = {k: v for k, v in page_data.items() if k != "same_site_paths"}

        for v in page_data.get("value_propositions", []):
            if v not in all_value_propositions:
                all_value_propositions.append(v)
        for p in page_data.get("partners", []):
            if p not in all_partners:
                all_partners.append(p)
        for b in page_data.get("trust_badges", []):
            if b not in all_trust_badges:
                all_trust_badges.append(b)
        if page_data.get("job_listings"):
            for j in page_data["job_listings"]:
                if not any(ex.get("title") == j.get("title") and ex.get("url") == j.get("url") for ex in job_listings):
                    job_listings.append(j)
        if page_data.get("team"):
            for t in page_data["team"]:
                if not any(ex.get("name") == t.get("name") for ex in team):
                    team.append(t)

        for k, v in (page_data.get("banner_stats") or {}).items():
            if v and k not in merged_banner_stats:
                merged_banner_stats[k] = v
        for k, v in (page_data.get("public_stats") or {}).items():
            if v and k not in merged_public_stats:
                merged_public_stats[k] = v

        for next_path in page_data.get("same_site_paths", []):
            next_path = next_path.split("#")[0].rstrip("/") or "/"
            if next_path not in visited and next_path not in queue:
                queue.append(next_path)

    merged_public_stats.update(_extract_public_stats_from_banner(merged_banner_stats))

    people_research: list[dict[str, Any]] = []
    if team and SCRAPE_RESEARCH_PEOPLE:
        logger.info("Researching %d team members (search + optional DuckDuckGo)", len(team))
        for p in team:
            res = _research_person(p.get("name", ""), p.get("title", ""))
            people_research.append(res)
            time.sleep(rate_limit_delay_sec)

    raw = {
        "url": base_url,
        "pages": pages,
        "banner_stats": merged_banner_stats,
        "public_stats": merged_public_stats,
        "value_propositions": all_value_propositions,
        "partners": all_partners,
        "trust_badges": all_trust_badges,
        "job_listings": job_listings,
        "team": team,
        "people_research": people_research,
    }
    return raw


def _clean_scrape_to_meaningful_stats(raw: dict[str, Any]) -> dict[str, Any]:
    """Build clean output: all banner/business stats, trust_badges, job_listings, team, people_research."""
    banner = raw.get("banner_stats", {})
    clean: dict[str, Any] = {
        "merchant_count": banner.get("merchant_count"),
        "credit_issued": banner.get("credit_issued"),
        "growth_rate": banner.get("growth_rate"),
        "nps_score": banner.get("nps_score"),
        "true_approvals_pct": banner.get("true_approvals_pct"),
        "conversion_lift_pct": banner.get("conversion_lift_pct"),
        "avg_sale_lift_pct": banner.get("avg_sale_lift_pct"),
        "value_propositions": raw.get("value_propositions", []),
        "partners": raw.get("partners", []),
        "trust_badges": raw.get("trust_badges", []),
        "job_listings": raw.get("job_listings", []),
        "team": raw.get("team", []),
        "people_research": raw.get("people_research", []),
        "pages_scraped": sorted(raw.get("pages", {}).keys()),
    }
    return clean


def scrape_and_save(
    raw_path: Path = CLARITYPAY_RAW_ARTIFACT,
    clean_path: Path = CLARITYPAY_CLEAN_ARTIFACT,
) -> dict[str, Any]:
    """Full-site scrape; save raw and clean. Returns clean dict (used in report)."""
    raw = scrape_claritypay()
    ensure_dir(raw_path)
    save_json(raw, raw_path)
    clean = _clean_scrape_to_meaningful_stats(raw)
    ensure_dir(clean_path)
    save_json(clean, clean_path)
    from src.config import CLARITYPAY_ARTIFACT
    save_json(clean, CLARITYPAY_ARTIFACT)
    logger.info(
        "ClarityPay scrape: %d pages, banner_stats=%s",
        len(clean.get("pages_scraped", [])),
        {k: v for k, v in clean.items() if k in ("merchant_count", "credit_issued", "growth_rate", "nps_score", "true_approvals_pct", "conversion_lift_pct", "avg_sale_lift_pct") and v},
    )
    return clean
