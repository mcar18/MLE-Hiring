"""
Train a baseline classifier for high dispute risk (e.g. LogisticRegression or RandomForest).
Target: high dispute risk = dispute_rate above threshold. Evaluate with ROC AUC, precision, recall.
Save model to artifacts/model.pkl.
"""
import logging
import pickle
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split

from src.config import ARTIFACTS_DIR, DISPUTE_RATE_HIGH_RISK_THRESHOLD, RANDOM_STATE, TEST_SIZE
from src.features.feature_builder import get_feature_columns
from src.utils.io_utils import ensure_dir

logger = logging.getLogger(__name__)


def make_target(df: pd.DataFrame, threshold: float = DISPUTE_RATE_HIGH_RISK_THRESHOLD) -> pd.Series:
    """Binary target: 1 if dispute_rate > threshold (high risk), else 0."""
    return (df["dispute_rate"] > threshold).astype(int)


def train_model(
    df: pd.DataFrame,
    target_col: str = "high_risk",
    model_path: Path | None = None,
    random_state: int = RANDOM_STATE,
    test_size: float = TEST_SIZE,
) -> tuple[object, dict]:
    """
    Train RandomForestClassifier. Optionally pass df with 'high_risk' already set, else we create it.
    Returns (fitted model, metrics dict with roc_auc, precision, recall).
    """
    if target_col not in df.columns:
        df = df.copy()
        df["high_risk"] = make_target(df)
    feature_cols = [c for c in get_feature_columns() if c in df.columns]
    if not feature_cols:
        raise ValueError("No feature columns found. Run feature_builder first.")
    X = df[feature_cols].fillna(0)
    y = df[target_col]
    stratify_arg = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify_arg
    )
    clf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=random_state)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    if hasattr(clf, "predict_proba"):
        proba = clf.predict_proba(X_test)
        y_proba = proba[:, 1] if proba.shape[1] > 1 else proba[:, 0]
    else:
        y_proba = y_pred

    roc_auc = roc_auc_score(y_test, y_proba) if y_test.nunique() > 1 else 0.0
    prec, rec, _, _ = precision_recall_fscore_support(y_test, y_pred, average="binary", zero_division=0)
    metrics = {"roc_auc": roc_auc, "precision": prec, "recall": rec}
    logger.info("Model metrics: ROC AUC=%.4f, precision=%.4f, recall=%.4f", roc_auc, prec, rec)

    model_path = model_path or ARTIFACTS_DIR / "model.pkl"
    ensure_dir(model_path)
    with open(model_path, "wb") as f:
        pickle.dump({"model": clf, "feature_columns": feature_cols, "threshold": DISPUTE_RATE_HIGH_RISK_THRESHOLD}, f)
    logger.info("Saved model: %s", model_path)
    return clf, metrics
