"""
Build structured report context for the LLM: portfolio summary, model metrics, top risk merchants,
risk drivers, scraped claritypay insights, PDF insights, assumptions, caveats.
"""
import json
import logging
from pathlib import Path

import pandas as pd

from src.config import (
    ARTIFACTS_DIR,
    CLARITYPAY_ARTIFACT,
    FEATURED_PARQUET,
    PDF_TEXT_JSON,
    PORTFOLIO_SUMMARY_JSON,
)
from src.utils.io_utils import load_json

logger = logging.getLogger(__name__)


def build_report_context(
    collated_path: Path | None = None,
    portfolio_path: Path = PORTFOLIO_SUMMARY_JSON,
    model_metrics: dict | None = None,
    pdf_text_path: Path = PDF_TEXT_JSON,
    claritypay_path: Path = CLARITYPAY_ARTIFACT,
    featured_path: Path | None = None,
) -> dict:
    """
    Assemble a single dict with all inputs the LLM needs. Load from artifact paths if not provided.
    If featured_path exists and has prob_high_risk, use it for top_risk; else use collated.
    """
    featured_path = featured_path or FEATURED_PARQUET
    collated_path = collated_path or ARTIFACTS_DIR / "collated.parquet"
    if featured_path.exists():
        df = pd.read_parquet(featured_path)
    elif collated_path.exists() and collated_path.suffix == ".parquet":
        df = pd.read_parquet(collated_path)
    else:
        df = pd.DataFrame()

    # Portfolio
    try:
        portfolio = load_json(portfolio_path)
    except FileNotFoundError:
        portfolio = {}

    # Top risk merchants (by prob_high_risk if present, else by dispute_rate)
    if "prob_high_risk" in df.columns:
        top_risk = (
            df.nlargest(10, "prob_high_risk")[["merchant_id", "country", "monthly_volume", "dispute_rate", "prob_high_risk"]]
            .fillna(0)
            .astype(object)
        )
        # Convert to native types for JSON
        top_risk = [{k: (float(v) if isinstance(v, (int, float)) else v) for k, v in row.items()} for row in top_risk.to_dict("records")]
    else:
        top_risk = (
            df.nlargest(10, "dispute_rate")[["merchant_id", "country", "monthly_volume", "dispute_rate"]]
            .fillna(0)
            .astype(object)
        )
        top_risk = [{k: (float(v) if isinstance(v, (int, float)) else v) for k, v in row.items()} for row in top_risk.to_dict("records")]

    # Risk drivers: high dispute_rate, high volume, internal_risk_flag
    risk_drivers = {
        "high_dispute_rate_merchants": int((df.get("dispute_rate", pd.Series(0)) > 0.002).sum()) if "dispute_rate" in df.columns else 0,
        "total_merchants": len(df),
        "internal_risk_breakdown": {str(k): int(v) for k, v in (df.get("internal_risk_flag", pd.Series()).value_counts().to_dict().items())} if "internal_risk_flag" in df.columns else {},
    }

    # PDF insights
    try:
        pdf_data = load_json(pdf_text_path)
        pdf_insights = pdf_data.get("text", "")[:2000]
    except FileNotFoundError:
        pdf_insights = "(PDF not processed)"

    # ClarityPay
    try:
        clarity = load_json(claritypay_path)
        claritypay_insights = {
            "value_propositions": clarity.get("value_propositions", []),
            "partners": clarity.get("partners", []),
            "public_stats": clarity.get("public_stats", {}),
        }
    except FileNotFoundError:
        claritypay_insights = {"value_propositions": [], "partners": [], "public_stats": {}}

    context = {
        "portfolio_summary": portfolio,
        "model_metrics": model_metrics or {},
        "top_risk_merchants": top_risk,
        "risk_drivers": risk_drivers,
        "scraped_claritypay_insights": claritypay_insights,
        "pdf_insights": pdf_insights,
        "assumptions": [
            "High dispute risk defined as dispute_rate > 0.002.",
            "Expected loss proxy uses 2% assumed loss rate on at-risk volume.",
            "REST Countries used for region/subregion enrichment; cache in memory.",
        ],
        "caveats": [
            "Sample data only; not representative of production.",
            "Model is baseline (Random Forest); no hyperparameter tuning.",
            "External context (ClarityPay) is scraped; site structure may change.",
        ],
    }
    return context
