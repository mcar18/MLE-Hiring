"""
LLM client: call OpenAI (or deterministic mock if OPENAI_API_KEY not set).
Secrets from environment via python-dotenv; never hardcode API keys.
"""
import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _mock_llm_response(prompt: str, context_preview: str) -> str:
    """
    Deterministic fallback when no API key: generate a minimal but valid report
    so the pipeline still produces artifacts.
    """
    return f"""# Underwriting Report (Mock — No API Key)

## Executive Summary
Portfolio risk has been assessed using the provided context. This is a **mock report** because no OPENAI_API_KEY was set. Run with a valid key for a full LLM-generated memo.

## Data & Methodology
Data sources: merchants CSV, internal mock API, REST Countries, PDF extract, ClarityPay scrape. Baseline Random Forest model for high dispute risk.

## Portfolio Risk Overview
See portfolio_summary in the report context for expected_high_risk_merchants, average_predicted_risk, and expected_loss_proxy.

## Top Risk Merchants
See top_risk_merchants in the context.

## Key Risk Drivers
See risk_drivers in the context.

## External Context (ClarityPay)
See scraped_claritypay_insights in the context.

## Document Insights (PDF)
See pdf_insights in the context.

## Recommendations & Controls
- Review high dispute-rate merchants quarterly.
- Set alerts for dispute_rate above 0.002.
- Monitor expected loss proxy vs actual chargebacks.

## Caveats
Model is baseline; sample data only. No hallucinated numbers in this mock.
"""


def call_llm(user_prompt: str, system_prompt: str) -> str:
    """
    Call OpenAI API if OPENAI_API_KEY is set; otherwise return mock response.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        logger.warning("OPENAI_API_KEY not set; using deterministic mock LLM response.")
        return _mock_llm_response(user_prompt, user_prompt[:500])

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=2000,
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.warning("OpenAI call failed: %s. Falling back to mock.", e)
        return _mock_llm_response(user_prompt, user_prompt[:500])
