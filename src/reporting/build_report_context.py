"""
Build structured report context for the LLM: portfolio summary, model comparison, top risk merchants,
feature importance, risk histogram summary, ClarityPay (clean), PDF summary, underwriting recommendation.
"""
import logging
from pathlib import Path

import pandas as pd

from src.config import (
    ARTIFACTS_DIR,
    CLARITYPAY_CLEAN_ARTIFACT,
    FEATURED_PARQUET,
    MODEL_COMPARISON_JSON,
    PDF_SUMMARY_JSON,
    PORTFOLIO_SUMMARY_JSON,
)
from src.utils.io_utils import load_json

logger = logging.getLogger(__name__)


def _compute_underwriting_recommendation(
    portfolio: dict,
    top_risk: list[dict],
    prob_col: str = "prob_high_risk",
) -> tuple[str, list[str]]:
    """
    Propose Approve / Approve with Conditions / Decline and conditions.
    Conditions: e.g. manual review if prob_high_risk > threshold or internal_risk_flag == high.
    """
    conditions: list[str] = []
    avg_risk = portfolio.get("average_predicted_risk") or 0
    expected_high = portfolio.get("expected_high_risk_merchants") or 0
    n = portfolio.get("n_merchants") or 1

    # High-risk count and share
    high_risk_share = expected_high / n if n else 0
    max_prob = max((m.get(prob_col) or 0) for m in top_risk) if top_risk else 0

    if avg_risk > 0.25 or high_risk_share > 0.2 or (top_risk and max_prob > 0.7):
        recommendation = "Decline"
        conditions.append("Portfolio-level risk exceeds acceptable threshold.")
    elif avg_risk > 0.1 or high_risk_share > 0.05 or (top_risk and max_prob > 0.5):
        recommendation = "Approve with Conditions"
        conditions.append("Manual review for merchants with prob_high_risk > 0.5.")
        conditions.append("Manual review for merchants with internal_risk_flag == high.")
    else:
        recommendation = "Approve"
        conditions.append("Standard monitoring; no conditions.")

    return recommendation, conditions


def build_report_context(
    collated_path: Path | None = None,
    portfolio_path: Path = PORTFOLIO_SUMMARY_JSON,
    model_metrics: dict | None = None,
    model_comparison_path: Path = MODEL_COMPARISON_JSON,
    pdf_summary_path: Path = PDF_SUMMARY_JSON,
    claritypay_path: Path = CLARITYPAY_CLEAN_ARTIFACT,
    featured_path: Path | None = None,
    feature_importance: list[tuple[str, float]] | None = None,
) -> dict:
    """
    Assemble a single dict with all inputs the LLM needs. Uses clean_scrape and pdf_summary.
    Includes model_comparison, top 10 by risk, feature_importance_ranking, portfolio_risk_histogram summary.
    """
    featured_path = featured_path or FEATURED_PARQUET
    collated_path = collated_path or ARTIFACTS_DIR / "collated.parquet"
    if featured_path.exists():
        df = pd.read_parquet(featured_path)
    elif collated_path.exists() and collated_path.suffix == ".parquet":
        df = pd.read_parquet(collated_path)
    else:
        df = pd.DataFrame()

    try:
        portfolio = load_json(portfolio_path)
    except FileNotFoundError:
        portfolio = {}

    # Top 10 merchants by predicted risk (OOF)
    if "prob_high_risk" in df.columns:
        cols = ["merchant_id", "country", "monthly_volume", "dispute_rate", "prob_high_risk"]
        if "internal_risk_flag" in df.columns:
            cols.append("internal_risk_flag")
        top_risk_df = df.nlargest(10, "prob_high_risk")[[c for c in cols if c in df.columns]].fillna(0)
        top_risk = [
            {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in row.items()}
            for row in top_risk_df.to_dict("records")
        ]
    else:
        top_risk = (
            df.nlargest(10, "dispute_rate")[["merchant_id", "country", "monthly_volume", "dispute_rate"]]
            .fillna(0)
            .astype(object)
        )
        top_risk = [{k: (float(v) if isinstance(v, (int, float)) else v) for k, v in row.items()} for row in top_risk.to_dict("records")]

    # Portfolio risk histogram summary (for report text)
    if "prob_high_risk" in df.columns:
        p = df["prob_high_risk"].fillna(0)
        portfolio_risk_histogram = {
            "min": float(p.min()),
            "max": float(p.max()),
            "mean": float(p.mean()),
            "median": float(p.median()),
            "p75": float(p.quantile(0.75)),
            "p90": float(p.quantile(0.90)),
        }
    else:
        portfolio_risk_histogram = {}

    risk_drivers = {
        "high_dispute_rate_merchants": int((df.get("dispute_rate", pd.Series(0)) > 0.002).sum()) if "dispute_rate" in df.columns else 0,
        "total_merchants": len(df),
        "internal_risk_breakdown": {str(k): int(v) for k, v in (df.get("internal_risk_flag", pd.Series()).value_counts().to_dict().items())} if "internal_risk_flag" in df.columns else {},
    }

    try:
        pdf_data = load_json(pdf_summary_path)
        pdf_insights = pdf_data.get("pdf_summary", "(PDF summary not available)")
    except FileNotFoundError:
        pdf_insights = "(PDF not processed)"

    try:
        clarity = load_json(claritypay_path)
        claritypay_insights = {
            "merchant_count": clarity.get("merchant_count"),
            "credit_issued": clarity.get("credit_issued"),
            "growth_rate": clarity.get("growth_rate"),
            "nps_score": clarity.get("nps_score"),
            "true_approvals_pct": clarity.get("true_approvals_pct"),
            "conversion_lift_pct": clarity.get("conversion_lift_pct"),
            "avg_sale_lift_pct": clarity.get("avg_sale_lift_pct"),
            "value_propositions": clarity.get("value_propositions", []),
            "partners": clarity.get("partners", []),
            "trust_badges": clarity.get("trust_badges", []),
            "job_listings": clarity.get("job_listings", []),
            "team": clarity.get("team", []),
            "investors_advisors": clarity.get("investors_advisors", []),
            "people_research": clarity.get("people_research", []),
            "pages_scraped": clarity.get("pages_scraped", []),
        }
    except FileNotFoundError:
        claritypay_insights = {"merchant_count": None, "credit_issued": None, "growth_rate": None, "nps_score": None, "true_approvals_pct": None, "conversion_lift_pct": None, "avg_sale_lift_pct": None, "value_propositions": [], "partners": [], "trust_badges": [], "job_listings": [], "team": [], "investors_advisors": [], "people_research": [], "pages_scraped": []}

    try:
        model_comparison = load_json(model_comparison_path)
    except FileNotFoundError:
        model_comparison = {}

    recommendation, conditions = _compute_underwriting_recommendation(portfolio, top_risk)

    feature_importance_ranking = feature_importance or []

    context = {
        "portfolio_summary": portfolio,
        "model_metrics": model_metrics or {},
        "model_comparison": model_comparison,
        "top_risk_merchants": top_risk,
        "risk_drivers": risk_drivers,
        "feature_importance_ranking": feature_importance_ranking,
        "portfolio_risk_histogram": portfolio_risk_histogram,
        "scraped_claritypay_insights": claritypay_insights,
        "pdf_insights": pdf_insights,
        "underwriting_recommendation": recommendation,
        "underwriting_conditions": conditions,
        "assumptions": [
            "High dispute risk defined as dispute_rate > 0.002.",
            "Expected loss proxy uses 2% assumed loss rate on at-risk volume.",
            "Out-of-fold predictions used for portfolio metrics.",
            "REST Countries used for region enrichment; cache in memory.",
        ],
        "caveats": [
            "Sample data only; not representative of production.",
            "Model comparison uses LogisticRegression vs RandomForest; chosen by ROC AUC.",
            "External context (ClarityPay) is scraped; site structure may change.",
        ],
    }
    return context
