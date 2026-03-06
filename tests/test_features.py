"""Feature engineering tests: divide-by-zero, missing values, encoding."""
import numpy as np
import pandas as pd
import pytest

from src.features.feature_builder import build_features, get_feature_columns, safe_divide


def test_safe_divide():
    assert safe_divide(10, 2) == 5.0
    assert safe_divide(10, 0) == 0.0
    assert safe_divide(10, 0, default=99.0) == 99.0
    assert safe_divide(0, 5) == 0.0


def test_build_features_handles_zero_transactions():
    df = pd.DataFrame({
        "merchant_id": ["M1", "M2"],
        "monthly_volume": [1000.0, 2000.0],
        "transaction_count": [0, 100],
        "dispute_count": [0, 2],
        "dispute_rate": [0.0, 0.02],
        "avg_ticket": [0.0, 20.0],
        "internal_risk_flag": ["low", "high"],
        "region": ["Europe", "Americas"],
    })
    out = build_features(df)
    assert "dispute_rate" in out.columns
    assert "volume_growth_proxy" in out.columns
    assert "internal_risk_flag_encoded" in out.columns
    assert "region_encoded" in out.columns
    assert not np.any(np.isinf(out["dispute_rate"]))
    assert not np.any(np.isinf(out["avg_ticket"]))


def test_build_features_missing_optional():
    df = pd.DataFrame({
        "merchant_id": ["M1"],
        "monthly_volume": [1000.0],
        "transaction_count": [100],
        "dispute_count": [1],
        "dispute_rate": [0.01],
        "avg_ticket": [10.0],
    })
    out = build_features(df)
    assert len(out) == 1
    assert out["volume_growth_proxy"].iloc[0] == 1.0  # default when last_30d missing
    assert out["internal_risk_flag_encoded"].iloc[0] == 0
    assert out["binary_high_internal_flag"].iloc[0] == 0


def test_get_feature_columns():
    cols = get_feature_columns()
    assert "dispute_rate" not in cols  # excluded to avoid target leakage
    assert "avg_ticket" in cols
    assert "monthly_volume" in cols
    assert "transaction_count" in cols
    assert "volume_growth_proxy" in cols
    assert "internal_risk_flag_encoded" in cols
    assert "region_encoded" in cols
    assert "log_monthly_volume" in cols
    assert "log_transaction_count" in cols
    assert "binary_high_internal_flag" in cols
    assert "volume_per_transaction" in cols
