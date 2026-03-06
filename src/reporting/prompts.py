"""
Prompt instructions for the LLM underwriting report.
Require: no hallucinated numbers, concise underwriting tone, decision-oriented recommendations.
Includes model comparison, feature importance, and underwriting recommendation (Approve / Approve with Conditions / Decline).
"""
SYSTEM_PROMPT = """You are a risk analyst writing a short underwriting memo for a BNPL (Buy Now Pay Later) merchant portfolio.
Use only the numbers and facts provided in the context. Do not invent or hallucinate any statistics.
Write in a concise, professional underwriting tone. End with a clear underwriting recommendation and conditions."""

REPORT_SECTIONS = """
The report must include these sections (use markdown headers). Keep the total report to 1–2 pages.

1. **Executive Summary** — 2–3 sentences on portfolio risk and key findings. State the underwriting recommendation (Approve / Approve with Conditions / Decline).

2. **Data Sources & Methodology** — Brief note on data sources (CSV, mock API, REST Countries, PDF, ClarityPay scrape) and how the risk model was built (out-of-fold evaluation, two baselines).

3. **Portfolio Risk Overview** — Use the portfolio summary numbers (expected high-risk count, average risk, expected loss proxy). Include the portfolio_risk_histogram summary (min, mean, median, p90) to describe risk distribution.

4. **Top Risk Merchants** — List the top 10 merchants by predicted risk from the context with their key metrics (merchant_id, country, monthly_volume, prob_high_risk, and internal_risk_flag if present).

5. **Key Risk Drivers** — Summarize risk_drivers (dispute rates, internal risk breakdown) and feature_importance_ranking (top drivers from the model).

6. **External Context (ClarityPay)** — One short paragraph using the clean scrape: merchant_count, credit_issued, growth_rate, nps_score, value_propositions, partners. Use only the numbers provided.

7. **Document Insights (PDF)** — One short paragraph using pdf_insights (the pdf_summary from the cleaned PDF). Do not invent content.

8. **Model Comparison** — One short paragraph comparing logistic_regression vs random_forest metrics (roc_auc, precision, recall, f1, brier_score) from model_comparison. State which model was chosen and why.

9. **Calibration & Probability Quality** — Use calibration_metrics from the context. Explain whether predicted probabilities appear roughly aligned with observed outcomes (e.g. from the calibration curve and Brier score). Note why calibration matters for underwriting thresholds (e.g. a 0.3 probability should correspond to ~30% observed high-risk rate when setting review cutoffs). State clearly that the small sample size limits confidence and that calibration results are illustrative only.

10. **Recommendations & Controls** — 3–5 bullet recommendations (e.g. review thresholds, monitoring). Include the underwriting_conditions from the context (e.g. manual review if prob_high_risk > 0.5, or if internal_risk_flag == high).

11. **Caveats & Assumptions** — List the caveats and assumptions provided. Add one line on model limitations.

**Underwriting Recommendation:** You must state clearly at the end: **Recommendation: [Approve | Approve with Conditions | Decline]** and list the conditions when applicable (from underwriting_conditions). Use only the recommendation and conditions from the context; do not invent new ones.
"""


def get_report_prompt(context_json: str) -> str:
    """Build the user prompt with context embedded."""
    return f"""Generate a 1–2 page underwriting memo for the risk team based on this structured context.

{REPORT_SECTIONS}

Context (JSON):
{context_json}

Write the report in markdown. Use only numbers from the context above. Do not make up statistics. Include the underwriting recommendation and conditions from the context."""