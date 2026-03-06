"""
Train baseline classifiers for high dispute risk. Label = dispute_rate > threshold (unchanged).
Target leakage fix: dispute_rate is NOT used as a feature; see get_feature_columns() in feature_builder.
We train LogisticRegression and RandomForest, compare by ROC AUC, and use out-of-fold predictions
for portfolio metrics to avoid overfitting.
"""
import logging
import pickle
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    f1_score,
    precision_recall_curve,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold

from src.config import (
    ARTIFACTS_DIR,
    DISPUTE_RATE_HIGH_RISK_THRESHOLD,
    MODEL_COMPARISON_JSON,
    RANDOM_STATE,
)
from src.features.feature_builder import get_feature_columns
from src.utils.io_utils import ensure_dir, save_json

logger = logging.getLogger(__name__)

N_FOLDS = 5


def make_target(df: pd.DataFrame, threshold: float = DISPUTE_RATE_HIGH_RISK_THRESHOLD) -> pd.Series:
    """Binary target: 1 if dispute_rate > threshold (high risk), else 0. Label definition unchanged."""
    return (df["dispute_rate"] > threshold).astype(int)


def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray) -> dict:
    """ROC AUC, precision, recall, F1. y_proba is probability of positive class."""
    roc_auc = roc_auc_score(y_true, y_proba) if np.unique(y_true).size > 1 else 0.0
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    return {"roc_auc": float(roc_auc), "precision": float(prec), "recall": float(rec), "f1_score": float(f1)}


def _out_of_fold_predictions(
    X: pd.DataFrame,
    y: pd.Series,
    model_factory: Callable[[], object],
    feature_cols: list[str],
    n_splits: int = N_FOLDS,
    random_state: int = RANDOM_STATE,
) -> tuple[np.ndarray, object, dict]:
    """
    Train on K-1 folds, predict on held-out fold; combine. Returns (oof_proba, fitted_model_for_save, metrics).
    n_splits is capped so as not to exceed n_samples (StratifiedKFold requirement).
    """
    n = len(X)
    n_splits = max(2, min(n_splits, n))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    oof_proba = np.zeros(len(X))
    fold_metrics: list[dict] = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        clf = model_factory()
        clf.fit(X_train, y_train)
        proba = clf.predict_proba(X_val)[:, 1] if hasattr(clf, "predict_proba") else clf.predict(X_val).astype(float)
        oof_proba[val_idx] = proba
        y_pred_val = (proba >= 0.5).astype(int)
        fold_metrics.append(_compute_metrics(y_val.values, y_pred_val, proba))

    # Aggregate metrics across folds (mean)
    mean_metrics = {
        "roc_auc": float(np.mean([m["roc_auc"] for m in fold_metrics])),
        "precision": float(np.mean([m["precision"] for m in fold_metrics])),
        "recall": float(np.mean([m["recall"] for m in fold_metrics])),
        "f1_score": float(np.mean([m["f1_score"] for m in fold_metrics])),
    }

    # Refit on full data for saving
    final_model = model_factory()
    final_model.fit(X, y)

    return oof_proba, final_model, mean_metrics


def train_model(
    df: pd.DataFrame,
    target_col: str = "high_risk",
    model_path: Path | None = None,
    random_state: int = RANDOM_STATE,
) -> tuple[object, dict, np.ndarray, dict, list[tuple[str, float]]]:
    """
    Train LogisticRegression and RandomForest; compare by ROC AUC; use OOF predictions for scoring.
    Returns (chosen_model, chosen_metrics, oof_proba, model_comparison_dict, feature_importance_list).
    Selection: better ROC AUC wins; if tie, better F1. Chosen model is saved to model.pkl.
    """
    if target_col not in df.columns:
        df = df.copy()
        df["high_risk"] = make_target(df)

    feature_cols = [c for c in get_feature_columns() if c in df.columns]
    if not feature_cols:
        raise ValueError("No feature columns found. Run feature_builder first.")

    X = df[feature_cols].fillna(0)
    y = df[target_col]

    if y.nunique() < 2:
        logger.warning("Only one class in target; skipping OOF and second model (LR requires 2 classes).")
        rf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=random_state)
        rf.fit(X, y)
        proba = rf.predict_proba(X)
        oof_proba = proba[:, 1] if proba.shape[1] > 1 else proba[:, 0]
        degenerate = {"roc_auc": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0}
        model_comparison = {"logistic_regression": degenerate, "random_forest": degenerate}
        ensure_dir(MODEL_COMPARISON_JSON)
        save_json(model_comparison, MODEL_COMPARISON_JSON)
        importance = list(zip(feature_cols, rf.feature_importances_.tolist()))
        importance.sort(key=lambda x: -x[1])
        model_path = model_path or ARTIFACTS_DIR / "model.pkl"
        ensure_dir(model_path)
        with open(model_path, "wb") as f:
            pickle.dump({
                "model": rf,
                "feature_columns": feature_cols,
                "threshold": DISPUTE_RATE_HIGH_RISK_THRESHOLD,
                "chosen_name": "random_forest",
            }, f)
        return rf, degenerate, oof_proba, model_comparison, importance

    def lr_factory():
        return LogisticRegression(max_iter=500, random_state=random_state)

    def rf_factory():
        return RandomForestClassifier(n_estimators=50, max_depth=5, random_state=random_state)

    # Out-of-fold for both models
    oof_lr, model_lr, metrics_lr = _out_of_fold_predictions(X, y, lr_factory, feature_cols, random_state=random_state)
    oof_rf, model_rf, metrics_rf = _out_of_fold_predictions(X, y, rf_factory, feature_cols, random_state=random_state)

    model_comparison = {
        "logistic_regression": metrics_lr,
        "random_forest": metrics_rf,
    }
    ensure_dir(MODEL_COMPARISON_JSON)
    save_json(model_comparison, MODEL_COMPARISON_JSON)
    logger.info("Model comparison: LR %s | RF %s", metrics_lr, metrics_rf)

    # Selection: better ROC AUC; if tie, better F1 (documented in code)
    if metrics_rf["roc_auc"] >= metrics_lr["roc_auc"]:
        if metrics_rf["roc_auc"] == metrics_lr["roc_auc"] and metrics_lr["f1_score"] > metrics_rf["f1_score"]:
            chosen_name, chosen_model, chosen_metrics, oof_proba = "logistic_regression", model_lr, metrics_lr, oof_lr
        else:
            chosen_name, chosen_model, chosen_metrics, oof_proba = "random_forest", model_rf, metrics_rf, oof_rf
    else:
        chosen_name, chosen_model, chosen_metrics, oof_proba = "logistic_regression", model_lr, metrics_lr, oof_lr

    logger.info("Chosen model: %s (ROC AUC=%.4f, F1=%.4f)", chosen_name, chosen_metrics["roc_auc"], chosen_metrics["f1_score"])

    # Feature importance: only for tree model; for LR we use abs(coef_). For RF we use feature_importances_
    if hasattr(chosen_model, "feature_importances_"):
        importance = list(zip(feature_cols, chosen_model.feature_importances_.tolist()))
    else:
        coef = getattr(chosen_model, "coef_", np.zeros((1, len(feature_cols))))
        imp = np.abs(coef).ravel()
        importance = list(zip(feature_cols, imp.tolist()))
    importance.sort(key=lambda x: -x[1])

    model_path = model_path or ARTIFACTS_DIR / "model.pkl"
    ensure_dir(model_path)
    with open(model_path, "wb") as f:
        pickle.dump({
            "model": chosen_model,
            "feature_columns": feature_cols,
            "threshold": DISPUTE_RATE_HIGH_RISK_THRESHOLD,
            "chosen_name": chosen_name,
        }, f)
    logger.info("Saved model: %s", model_path)

    return chosen_model, chosen_metrics, oof_proba, model_comparison, importance
