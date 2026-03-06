"""
Scrape claritypay.com: value propositions, partner names, public statistics.
Best practices: User-Agent, timeouts, rate limiting. Store parsed results in artifacts.
"""
import logging
import re
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.config import (
    CLARITYPAY_ARTIFACT,
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
    Fetch claritypay.com and parse value propositions, partners, and public stats.
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

    # Heuristics: look for headings and list items that sound like value props
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

    # Partners: common patterns like "Proud Partner", logos alt text, etc.
    for tag in soup.find_all(["img", "span", "div"]):
        alt = tag.get("alt") or ""
        text = (tag.get_text() or alt).strip()
        if "partner" in (text + alt).lower() or "logo" in alt.lower():
            if alt and alt not in partners:
                partners.append(alt)
            elif text and len(text) < 50 and text not in partners:
                partners.append(text)

    # Public stats: numbers like "1900+", "$1.2B+", "305K"
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


def scrape_and_save(output_path: Path = CLARITYPAY_ARTIFACT) -> dict[str, Any]:
    """Scrape ClarityPay and save to artifacts. Returns parsed dict."""
    data = scrape_claritypay()
    ensure_dir(output_path)
    save_json(data, output_path)
    return data
