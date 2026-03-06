"""
REST Countries API client. Enriches merchant country with region, subregion, country_code.
Uses caching to avoid repeated calls; timeout and retry handling.
"""
import logging
from typing import Any
from urllib.parse import quote

import requests

from src.config import REST_COUNTRIES_BASE, REST_COUNTRIES_TIMEOUT_SEC, REST_COUNTRIES_RETRIES
from src.utils.retry_utils import with_retry

logger = logging.getLogger(__name__)

# In-memory cache: country name -> enrichment dict. Production would use Redis or similar.
_country_cache: dict[str, dict[str, Any]] = {}


def _normalize_country_for_api(country: str) -> str:
    """Map our country names to what REST Countries accepts (e.g. full name)."""
    return country.strip()


def fetch_country_enrichment(country: str) -> dict[str, Any] | None:
    """
    Call REST Countries API by country name. Return region, subregion, country code.
    Cached per country. Returns None on failure.
    """
    key = _normalize_country_for_api(country)
    if key in _country_cache:
        return _country_cache[key]

    def _get() -> dict[str, Any]:
        # Use name endpoint; API returns list of matches
        url = f"{REST_COUNTRIES_BASE}/name/{quote(key)}"
        resp = requests.get(url, timeout=REST_COUNTRIES_TIMEOUT_SEC, params={"fullText": "true"})
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError(f"No country found for: {key}")
        first = data[0]
        out = {
            "region": first.get("region"),
            "subregion": first.get("subregion"),
            "country_code": first.get("cca2"),
        }
        return out

    try:
        result = with_retry(
            _get,
            max_retries=REST_COUNTRIES_RETRIES,
            allowed_exceptions=(requests.RequestException, ValueError, KeyError),
        )
        _country_cache[key] = result
        return result
    except Exception as e:
        logger.warning("REST Countries failed for %s: %s", country, e)
        _country_cache[key] = {}  # cache miss to avoid hammering
        return None
