"""Model training pipeline tests."""
import pandas as pd
import pytest

from src.config import DISPUTE_RATE_HIGH_RISK_THRESHOLD
from src.features.feature_builder import build_features
from src.modeling.train_model import make_target, train_model


@pytest.fixture
def sample_feature_df():
    """DataFrame with features and target for training."""
    n = 40
    df = pd.DataFrame({
        "merchant_id": [f"M{i:03d}" for i in range(n)],
        "monthly_volume": [50000.0 + i * 1000 for i in range(n)],
        "transaction_count": [1000 + i * 50 for i in range(n)],
        "dispute_count": [0] * 30 + [5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        "dispute_rate": [0.0] * 30 + [0.005, 0.006, 0.007, 0.008, 0.009, 0.01, 0.011, 0.012, 0.013, 0.014],
        "avg_ticket": [50.0] * n,
        "internal_risk_flag": ["low"] * 25 + ["medium"] * 10 + ["high"] * 5,
        "region": ["Europe"] * 20 + ["Americas"] * 20,
    })
    df.loc[df.index[30:], "dispute_count"] = (df.loc[df.index[30:], "transaction_count"] * 0.005).astype(int).clip(1, 100)
    df["dispute_rate"] = df["dispute_count"] / df["transaction_count"]
    return build_features(df)


def test_make_target(sample_feature_df):
    y = make_target(sample_feature_df, threshold=DISPUTE_RATE_HIGH_RISK_THRESHOLD)
    assert y.dtype in (int, "int32", "int64")
    assert set(y.unique()).issubset({0, 1})
    assert y.sum() >= 0


def test_train_model_returns_metrics_and_model(sample_feature_df):
    model, metrics = train_model(sample_feature_df)
    assert "roc_auc" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert hasattr(model, "predict")
    assert 0 <= metrics["roc_auc"] <= 1
    assert 0 <= metrics["precision"] <= 1
    assert 0 <= metrics["recall"] <= 1


def test_train_model_single_class():
    """When all labels are same, stratify is skipped and training still runs."""
    df = pd.DataFrame({
        "merchant_id": ["M1", "M2", "M3"],
        "monthly_volume": [1000.0, 2000.0, 3000.0],
        "transaction_count": [100, 200, 300],
        "dispute_count": [0, 0, 0],
        "dispute_rate": [0.0, 0.0, 0.0],
        "avg_ticket": [10.0, 10.0, 10.0],
        "internal_risk_flag_encoded": [0, 0, 0],
        "region_encoded": [0, 0, 0],
        "volume_growth_proxy": [1.0, 1.0, 1.0],
        "high_risk": [0, 0, 0],
    })
    model, metrics = train_model(df, target_col="high_risk")
    assert model is not None
    assert "roc_auc" in metrics
