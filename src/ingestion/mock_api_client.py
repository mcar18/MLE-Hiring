"""
Mock internal API client. Calls the FastAPI service per merchant with timeout and retry.
Validates responses with jsonschema against data/simulated_api_contract.json.
"""
import logging
from pathlib import Path
from typing import Any

import requests

from src.config import (
    MOCK_API_BASE_URL,
    MOCK_API_RETRIES,
    MOCK_API_TIMEOUT_SEC,
    SIMULATED_API_CONTRACT,
)
from src.validation.validators import load_and_validate_api_contract, validate_mock_api_response
from src.utils.retry_utils import with_retry

logger = logging.getLogger(__name__)


def fetch_merchant_from_mock_api(
    merchant_id: str,
    base_url: str = MOCK_API_BASE_URL,
    timeout_sec: int = MOCK_API_TIMEOUT_SEC,
    contract_path: Path = SIMULATED_API_CONTRACT,
) -> dict[str, Any] | None:
    """
    Call GET /merchants/{merchant_id} on the mock API. Validate response with contract.
    Returns response dict or None on failure (logged).
    """
    contract = load_and_validate_api_contract(contract_path)

    def _get() -> dict[str, Any]:
        url = f"{base_url.rstrip('/')}/merchants/{merchant_id}"
        resp = requests.get(url, timeout=timeout_sec)
        resp.raise_for_status()
        data = resp.json()
        ok, err = validate_mock_api_response(data, contract)
        if not ok:
            raise ValueError(f"Contract validation failed: {err}")
        return data

    try:
        return with_retry(
            _get,
            max_retries=MOCK_API_RETRIES,
            allowed_exceptions=(requests.RequestException, ValueError),
        )
    except Exception as e:
        logger.warning("Mock API failed for merchant %s: %s", merchant_id, e)
        return None
