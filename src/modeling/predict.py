"""
Load saved model and predict high-risk probability for a DataFrame.
"""
import logging
import pickle
from pathlib import Path

import pandas as pd

from src.config import MODEL_PKL

logger = logging.getLogger(__name__)


def load_model(path: Path = MODEL_PKL) -> dict:
    """Load model artifact (dict with 'model', 'feature_columns', 'threshold')."""
    with open(path, "rb") as f:
        return pickle.load(f)


def predict_risk(df: pd.DataFrame, model_path: Path = MODEL_PKL) -> pd.Series:
    """Return predicted probability of high dispute risk for each row."""
    blob = load_model(model_path)
    model = blob["model"]
    feature_cols = blob["feature_columns"]
    X = df[[c for c in feature_cols if c in df.columns]].reindex(columns=feature_cols).fillna(0)
    if hasattr(model, "predict_proba"):
        return pd.Series(model.predict_proba(X)[:, 1], index=df.index)
    return pd.Series(model.predict(X), index=df.index)
