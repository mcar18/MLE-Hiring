"""
Validators: apply schemas to DataFrames and API responses.
Reject malformed rows and log errors for governance.
"""
import json
import logging
from pathlib import Path
from typing import Any

import jsonschema
import pandas as pd

from src.validation.schemas import CollatedMerchantSchema, MerchantRowSchema

logger = logging.getLogger(__name__)


def validate_merchant_row(row: pd.Series) -> tuple[bool, str | None]:
    """
    Validate a single CSV row with MerchantRowSchema.
    Returns (is_valid, error_message). error_message is None when valid.
    """
    try:
        d = row.to_dict()
        # Coerce for pydantic: ensure numeric types
        if "registration_number" in d and (pd.isna(d["registration_number"]) or d["registration_number"] == ""):
            d["registration_number"] = None
        else:
            d["registration_number"] = str(d.get("registration_number", "") or "").strip() or None
        d["monthly_volume"] = float(d["monthly_volume"])
        d["dispute_count"] = int(d["dispute_count"])
        d["transaction_count"] = int(d["transaction_count"])
        MerchantRowSchema.model_validate(d)
        return True, None
    except Exception as e:
        return False, str(e)


def validate_csv_and_filter(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """
    Validate each row of the merchants DataFrame. Return valid DataFrame and list of errors.
    Invalid rows are dropped and logged.
    """
    errors: list[dict[str, Any]] = []
    valid_indices: list[int] = []
    for idx, row in df.iterrows():
        ok, err = validate_merchant_row(row)
        if ok:
            valid_indices.append(idx)
        else:
            errors.append({"index": int(idx), "merchant_id": str(row.get("merchant_id", "")), "error": err})
            logger.warning("CSV validation failed for row %s (%s): %s", idx, row.get("merchant_id"), err)
    valid_df = df.loc[valid_indices].copy()
    return valid_df, errors


def load_and_validate_api_contract(contract_path: Path) -> dict[str, Any]:
    """Load JSON Schema from simulated_api_contract.json for API response validation."""
    with open(contract_path, encoding="utf-8") as f:
        return json.load(f)


def validate_mock_api_response(response_json: dict[str, Any], contract: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate mock API response against JSON Schema contract.
    Returns (is_valid, error_message).
    """
    try:
        jsonschema.validate(instance=response_json, schema=contract)
        return True, None
    except jsonschema.ValidationError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


def validate_collated_row(row: pd.Series) -> tuple[bool, str | None]:
    """Validate a collated row (e.g. for writing or downstream). Returns (is_valid, error_message)."""
    try:
        d = row.to_dict()
        # Optional fields can be NaN
        for k in list(d.keys()):
            if pd.isna(d[k]) and k not in ("region", "subregion", "country_code", "internal_risk_flag",
                                           "last_30d_volume", "last_30d_txn_count", "avg_ticket_size",
                                           "last_review_date", "volume_growth_proxy"):
                continue
            if pd.isna(d[k]):
                d[k] = None
        d["dispute_rate"] = float(d["dispute_rate"])
        d["avg_ticket"] = float(d["avg_ticket"])
        d["monthly_volume"] = float(d["monthly_volume"])
        d["transaction_count"] = int(d["transaction_count"])
        d["dispute_count"] = int(d["dispute_count"])
        CollatedMerchantSchema.model_validate(d)
        return True, None
    except Exception as e:
        return False, str(e)
