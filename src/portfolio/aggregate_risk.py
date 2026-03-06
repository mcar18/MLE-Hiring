"""
Portfolio risk aggregation: expected_high_risk_merchants, average_predicted_risk, expected_loss_proxy.
Save to artifacts/portfolio_summary.json.
"""
import logging
from pathlib import Path

import pandas as pd

from src.config import ARTIFACTS_DIR, ASSUMED_LOSS_RATE
from src.utils.io_utils import ensure_dir, save_json

logger = logging.getLogger(__name__)


def aggregate_risk(
    df: pd.DataFrame,
    prob_col: str = "prob_high_risk",
    volume_col: str = "monthly_volume",
    assumed_loss_rate: float = ASSUMED_LOSS_RATE,
) -> dict:
    """
    Compute portfolio metrics:
    - expected_high_risk_merchants = sum(prob_high_risk)
    - average_predicted_risk = mean(prob_high_risk)
    - expected_loss_proxy = sum(prob_high_risk * monthly_volume * assumed_loss_rate)
    """
    if prob_col not in df.columns:
        raise ValueError(f"DataFrame must have column '{prob_col}' (run predict first).")
    p = df[prob_col].fillna(0)
    vol = df[volume_col].fillna(0)
    expected_high_risk_merchants = float(p.sum())
    average_predicted_risk = float(p.mean())
    expected_loss_proxy = float((p * vol * assumed_loss_rate).sum())
    out = {
        "expected_high_risk_merchants": expected_high_risk_merchants,
        "average_predicted_risk": average_predicted_risk,
        "expected_loss_proxy": expected_loss_proxy,
        "assumed_loss_rate": assumed_loss_rate,
        "n_merchants": int(len(df)),
    }
    logger.info(
        "Portfolio: expected_high_risk=%.2f, avg_risk=%.4f, expected_loss_proxy=%.2f",
        out["expected_high_risk_merchants"],
        out["average_predicted_risk"],
        out["expected_loss_proxy"],
    )
    return out


def save_portfolio_summary(metrics: dict, path: Path | None = None) -> Path:
    """Write portfolio summary to JSON."""
    path = path or ARTIFACTS_DIR / "portfolio_summary.json"
    ensure_dir(path)
    save_json(metrics, path)
    return path
