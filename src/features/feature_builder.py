"""
Feature engineering from collated data: dispute_rate, avg_ticket, volume_growth_proxy.
Encode internal_risk_flag and region. Handle divide-by-zero and missing values safely.
"""
import logging
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)

# Columns we need for features (must exist after collation)
REQUIRED_COLS = [
    "merchant_id",
    "monthly_volume",
    "transaction_count",
    "dispute_count",
    "dispute_rate",
    "avg_ticket",
]
OPTIONAL_FOR_FEATURES = ["last_30d_volume", "internal_risk_flag", "region"]


def safe_divide(num: float, denom: float, default: float = 0.0) -> float:
    """Return num/denom or default if denom is 0 or NaN."""
    if denom is None or pd.isna(denom) or denom == 0:
        return default
    if num is None or pd.isna(num):
        return default
    return float(num) / float(denom)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    From collated DataFrame build model features:
    - dispute_rate, avg_ticket (already in collated; ensure no inf/nan)
    - volume_growth_proxy = last_30d_volume / monthly_volume
    - Encoded: internal_risk_flag (label/categorical), region (label/categorical)
    Handle divide-by-zero and missing values safely.
    """
    out = df.copy()
    # Ensure dispute_rate and avg_ticket exist and are safe
    if "dispute_rate" not in out.columns:
        out["dispute_rate"] = out.apply(
            lambda r: safe_divide(r.get("dispute_count", 0), r.get("transaction_count", 1)), axis=1
        )
    if "avg_ticket" not in out.columns:
        out["avg_ticket"] = out.apply(
            lambda r: safe_divide(r.get("monthly_volume", 0), r.get("transaction_count", 1)), axis=1
        )
    out["dispute_rate"] = out["dispute_rate"].fillna(0).replace([float("inf"), float("-inf")], 0).clip(0, 1)
    out["avg_ticket"] = out["avg_ticket"].fillna(0).replace([float("inf"), float("-inf")], 0).clip(0, 1e12)

    # volume_growth_proxy
    out["volume_growth_proxy"] = out.apply(
        lambda r: safe_divide(
            r.get("last_30d_volume") or r.get("monthly_volume"),
            r.get("monthly_volume"),
            default=1.0,
        ),
        axis=1,
    )
    out["volume_growth_proxy"] = out["volume_growth_proxy"].fillna(1.0).replace([float("inf"), float("-inf")], 1.0)

    # Encode internal_risk_flag: map to 0/1/2
    risk_map = {"low": 0, "medium": 1, "high": 2}
    risk_series = out.get("internal_risk_flag")
    if risk_series is None:
        out["internal_risk_flag_encoded"] = 0
    else:
        out["internal_risk_flag_encoded"] = (
            risk_series.map(lambda x: risk_map.get(str(x).lower() if pd.notna(x) else "low", 0))
            .fillna(0)
            .astype(int)
        )

    # Encode region: categorical -> numeric (factorize)
    region_series = out.get("region")
    if region_series is None:
        region_series = pd.Series(["Unknown"] * len(out), index=out.index)
    else:
        region_series = region_series.fillna("Unknown")
    out["region_encoded"], _ = pd.factorize(region_series)

    logger.info("Built features: dispute_rate, avg_ticket, volume_growth_proxy, internal_risk_flag_encoded, region_encoded")
    return out


def get_feature_columns() -> List[str]:
    """Column names used as model features (numeric)."""
    return ["dispute_rate", "avg_ticket", "volume_growth_proxy", "internal_risk_flag_encoded", "region_encoded"]
