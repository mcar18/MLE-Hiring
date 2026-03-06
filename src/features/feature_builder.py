"""
Feature engineering from collated data.
Target leakage fix: dispute_rate is used ONLY for the label (high_risk); it is NOT a feature.
Features used for training: monthly_volume, transaction_count, avg_ticket, volume_growth_proxy,
internal_risk_flag_encoded, region_encoded, plus log_*, binary_high_internal_flag, volume_per_transaction.
"""
import logging
from typing import List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

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


def safe_log(x: float, default: float = 0.0) -> float:
    """Return log(1 + x) for non-negative x; default for NaN/neg."""
    if x is None or pd.isna(x) or x < 0:
        return default
    return float(np.log1p(x))


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build model features. dispute_rate is kept in the DataFrame for target creation only
    and is explicitly excluded from get_feature_columns() to avoid target leakage.
    """
    out = df.copy()

    # --- Derived fields (safe divide-by-zero) ---
    if "dispute_rate" not in out.columns:
        out["dispute_rate"] = out.apply(
            lambda r: safe_divide(r.get("dispute_count", 0), r.get("transaction_count", 1)), axis=1
        )
    if "avg_ticket" not in out.columns:
        out["avg_ticket"] = out.apply(
            lambda r: safe_divide(r.get("monthly_volume", 0), r.get("transaction_count", 1)), axis=1
        )
    out["dispute_rate"] = out["dispute_rate"].fillna(0).replace([np.inf, -np.inf], 0).clip(0, 1)
    out["avg_ticket"] = out["avg_ticket"].fillna(0).replace([np.inf, -np.inf], 0).clip(0, 1e12)

    # volume_growth_proxy: recent vs typical volume; >1 suggests growth (business intuition: growth can correlate with risk)
    out["volume_growth_proxy"] = out.apply(
        lambda r: safe_divide(
            r.get("last_30d_volume") or r.get("monthly_volume"),
            r.get("monthly_volume"),
            default=1.0,
        ),
        axis=1,
    )
    out["volume_growth_proxy"] = out["volume_growth_proxy"].fillna(1.0).replace([np.inf, -np.inf], 1.0)

    # volume_per_transaction: same as avg_ticket but explicit; scale-invariant measure of ticket size (business: large tickets can mean different risk profile)
    out["volume_per_transaction"] = out.apply(
        lambda r: safe_divide(r.get("monthly_volume", 0), r.get("transaction_count", 1), default=0.0), axis=1
    )
    out["volume_per_transaction"] = out["volume_per_transaction"].fillna(0).replace([np.inf, -np.inf], 0).clip(0, 1e12)

    # --- Encodings ---
    risk_map = {"low": 0, "medium": 1, "high": 2}
    risk_series = out.get("internal_risk_flag")
    if risk_series is None:
        out["internal_risk_flag_encoded"] = 0
        out["binary_high_internal_flag"] = 0
    else:
        out["internal_risk_flag_encoded"] = (
            risk_series.map(lambda x: risk_map.get(str(x).lower() if pd.notna(x) else "low", 0))
            .fillna(0)
            .astype(int)
        )
        # binary_high_internal_flag: 1 if internal system already flags high risk (business: strong signal for underwriting)
        out["binary_high_internal_flag"] = (out["internal_risk_flag_encoded"] == 2).astype(int)

    region_series = out.get("region")
    if region_series is None:
        region_series = pd.Series(["Unknown"] * len(out), index=out.index)
    else:
        region_series = region_series.fillna("Unknown")
    out["region_encoded"], _ = pd.factorize(region_series)

    # --- Log features: reduce skew, optional but often help linear models (business: volume/scale on log scale) ---
    vol = out.get("monthly_volume", pd.Series(0, index=out.index)).fillna(0).clip(lower=0)
    txn = out.get("transaction_count", pd.Series(1, index=out.index)).fillna(1).clip(lower=0)
    out["log_monthly_volume"] = vol.apply(lambda x: safe_log(x))
    out["log_transaction_count"] = txn.apply(lambda x: safe_log(x))

    logger.info(
        "Built features (no dispute_rate to avoid target leakage): %s",
        ", ".join(get_feature_columns()),
    )
    return out


def get_feature_columns() -> List[str]:
    """
    Column names used as model features. Explicitly EXCLUDES dispute_rate to prevent target leakage:
    the label high_risk is derived from dispute_rate, so using it as a feature would be leakage.
    """
    return [
        "monthly_volume",
        "transaction_count",
        "avg_ticket",
        "volume_growth_proxy",
        "internal_risk_flag_encoded",
        "region_encoded",
        "log_monthly_volume",
        "log_transaction_count",
        "binary_high_internal_flag",
        "volume_per_transaction",
    ]
