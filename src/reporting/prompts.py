"""
Prompt instructions for the LLM underwriting report.
Require: no hallucinated numbers, concise underwriting tone, decision-oriented recommendations.
"""
SYSTEM_PROMPT = """You are a risk analyst writing a short underwriting memo for a BNPL (Buy Now Pay Later) merchant portfolio.
Use only the numbers and facts provided in the context. Do not invent or hallucinate any statistics.
Write in a concise, professional underwriting tone. End with clear, decision-oriented recommendations."""

REPORT_SECTIONS = """
The report must include these sections (use markdown headers):

1. **Executive Summary** — 2–3 sentences on portfolio risk and key findings.
2. **Data & Methodology** — Brief note on data sources and how the risk model was built.
3. **Portfolio Risk Overview** — Use the portfolio summary numbers provided (expected high-risk count, average risk, expected loss proxy).
4. **Top Risk Merchants** — List the top risk merchants from the context with their key metrics.
5. **Key Risk Drivers** — Summarize dispute rates, internal risk flags, and volume.
6. **External Context (ClarityPay)** — One short paragraph on value propositions/partners/stats from the scraped data.
7. **Document Insights (PDF)** — One short paragraph on what the sample PDF says (if any).
8. **Recommendations & Controls** — 3–5 bullet recommendations (e.g. review thresholds, monitoring).
9. **Caveats** — List the caveats provided; add one on model limitations.

Keep the total report to 1–2 pages. Be concise."""

def get_report_prompt(context_json: str) -> str:
    """Build the user prompt with context embedded."""
    return f"""Generate a 1–2 page underwriting memo for the risk team based on this structured context.

{REPORT_SECTIONS}

Context (JSON):
{context_json}

Write the report in markdown. Use only numbers from the context above. Do not make up statistics."""
