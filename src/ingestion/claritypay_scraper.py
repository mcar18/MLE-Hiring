"""
Scrape claritypay.com: value propositions, partner names, public statistics.
Save raw output to raw_scrape.json; produce clean_scrape.json with only meaningful stats
(merchant_count, credit_issued, growth_rate, nps_score). Report uses clean_scrape.
"""
import logging
import re
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.config import (
    CLARITYPAY_CLEAN_ARTIFACT,
    CLARITYPAY_RAW_ARTIFACT,
    CLARITYPAY_URL,
    SCRAPE_RATE_LIMIT_DELAY_SEC,
    SCRAPE_TIMEOUT_SEC,
    USER_AGENT,
)
from src.utils.io_utils import ensure_dir, save_json

logger = logging.getLogger(__name__)


def scrape_claritypay(
    base_url: str = CLARITYPAY_URL,
    timeout_sec: int = SCRAPE_TIMEOUT_SEC,
    user_agent: str = USER_AGENT,
    rate_limit_delay_sec: float = SCRAPE_RATE_LIMIT_DELAY_SEC,
) -> dict[str, Any]:
    """
    Fetch claritypay.com and parse value propositions, partners, and public stats (raw).
    Returns structured dict. Respectful: one request, User-Agent, timeout.
    """
    headers = {"User-Agent": user_agent}
    try:
        resp = requests.get(base_url, headers=headers, timeout=timeout_sec)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("ClarityPay fetch failed: %s", e)
        return {"error": str(e), "value_propositions": [], "partners": [], "public_stats": {}}

    time.sleep(rate_limit_delay_sec)

    soup = BeautifulSoup(resp.text, "html.parser")
    value_propositions: list[str] = []
    partners: list[str] = []
    public_stats: dict[str, str] = {}

    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = (tag.get_text() or "").strip()
        if not text or len(text) > 200:
            continue
        lower = text.lower()
        if any(
            x in lower
            for x in (
                "pay over time",
                "clear terms",
                "flexible",
                "credit",
                "bnpl",
                "buy now",
                "merchant",
                "customer",
            )
        ):
            if text not in value_propositions:
                value_propositions.append(text)

    for tag in soup.find_all(["img", "span", "div"]):
        alt = tag.get("alt") or ""
        text = (tag.get_text() or alt).strip()
        if "partner" in (text + alt).lower() or "logo" in alt.lower():
            if alt and alt not in partners:
                partners.append(alt)
            elif text and len(text) < 50 and text not in partners:
                partners.append(text)

    num_pattern = re.compile(r"[\$]?[\d,]+\.?\d*[KMB+]?")
    for tag in soup.find_all(string=True):
        s = (tag if isinstance(tag, str) else tag.get_text() or "").strip()
        if not s:
            continue
        matches = num_pattern.findall(s)
        if matches and any(c.isdigit() for c in s):
            for m in matches:
                if m not in public_stats and len(m) <= 20:
                    public_stats[m] = s[:100]

    out = {
        "url": base_url,
        "value_propositions": value_propositions[:15],
        "partners": partners[:20],
        "public_stats": dict(list(public_stats.items())[:10]),
    }
    return out


def _clean_scrape_to_meaningful_stats(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Extract only meaningful stats: merchant_count, credit_issued, growth_rate, nps_score.
    Ignore script metadata, timestamps, unrelated numbers. Use heuristics on raw text.
    """
    clean: dict[str, Any] = {
        "merchant_count": None,
        "credit_issued": None,
        "growth_rate": None,
        "nps_score": None,
        "value_propositions": raw.get("value_propositions", [])[:10],
        "partners": raw.get("partners", [])[:10],
    }
    stats = raw.get("public_stats", {})
    text_sources = list(stats.values()) + raw.get("value_propositions", [])

    # merchant_count: look for "merchant" + number (e.g. "1900+ Merchants")
    for s in text_sources:
        if "merchant" in s.lower() and re.search(r"[\d,]+\.?\d*[KMB+]?", s):
            m = re.search(r"([\d,]+\.?\d*[KMB+]?)", s)
            if m:
                clean["merchant_count"] = m.group(1).strip()
                break

    # credit_issued: $ amount (e.g. "$1.2B+ Credit Issued")
    for s in text_sources:
        if ("credit" in s.lower() or "issued" in s.lower()) and "$" in s:
            m = re.search(r"\$[\d,]+\.?\d*[KMB+]?", s)
            if m:
                clean["credit_issued"] = m.group(0)
                break

    # growth_rate: % growth
    for s in text_sources:
        if "growth" in s.lower() and re.search(r"\d+%?", s):
            m = re.search(r"(\d+%?)", s)
            if m:
                clean["growth_rate"] = m.group(1)
                break

    # nps_score: NPS or net promoter
    for s in text_sources:
        if "nps" in s.lower() or "net promoter" in s.lower():
            m = re.search(r"\d+", s)
            if m:
                clean["nps_score"] = m.group(0)
                break

    # Fallback: take first dollar amount for credit, first large number for merchants
    if clean["credit_issued"] is None:
        for k, v in stats.items():
            if k.startswith("$") and len(k) <= 15:
                clean["credit_issued"] = k
                break
    if clean["merchant_count"] is None:
        for k, v in stats.items():
            if re.match(r"^[\d,]+\.?\d*[KMB+]?$", k) and not k.startswith("$"):
                clean["merchant_count"] = k
                break

    return clean


def scrape_and_save(
    raw_path: Path = CLARITYPAY_RAW_ARTIFACT,
    clean_path: Path = CLARITYPAY_CLEAN_ARTIFACT,
) -> dict[str, Any]:
    """Scrape ClarityPay; save raw and clean outputs. Returns clean dict (used in report)."""
    raw = scrape_claritypay()
    ensure_dir(raw_path)
    save_json(raw, raw_path)
    clean = _clean_scrape_to_meaningful_stats(raw)
    ensure_dir(clean_path)
    save_json(clean, clean_path)
    # Keep backward compatibility: also write to legacy path for any code that expects it
    from src.config import CLARITYPAY_ARTIFACT
    save_json(clean, CLARITYPAY_ARTIFACT)
    return clean
