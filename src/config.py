"""
Central configuration for the merchant underwriting pipeline.
Paths and settings are defined here for a single source of truth.
"""
from pathlib import Path

# Project root (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data paths
DATA_DIR = PROJECT_ROOT / "data"
MERCHANTS_CSV = DATA_DIR / "merchants.csv"
SAMPLE_PDF = DATA_DIR / "sample_merchant_summary.pdf"
SIMULATED_API_CONTRACT = DATA_DIR / "simulated_api_contract.json"

# Artifacts (pipeline outputs)
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
PDF_TEXT_JSON = ARTIFACTS_DIR / "pdf_text.json"
COLLATED_PARQUET = ARTIFACTS_DIR / "collated.parquet"
FEATURED_PARQUET = ARTIFACTS_DIR / "featured.parquet"
MODEL_PKL = ARTIFACTS_DIR / "model.pkl"
PORTFOLIO_SUMMARY_JSON = ARTIFACTS_DIR / "portfolio_summary.json"
REPORT_CONTEXT_JSON = ARTIFACTS_DIR / "report_context.json"
UNDERWRITING_REPORT_MD = ARTIFACTS_DIR / "underwriting_report.md"
LLM_PROMPT_TXT = ARTIFACTS_DIR / "llm_prompt.txt"
LLM_RESPONSE_TXT = ARTIFACTS_DIR / "llm_response.txt"
CLARITYPAY_ARTIFACT = ARTIFACTS_DIR / "claritypay_parsed.json"

# Mock API (pipeline calls this)
MOCK_API_BASE_URL = "http://127.0.0.1:8000"
MOCK_API_TIMEOUT_SEC = 10
MOCK_API_RETRIES = 3

# REST Countries
REST_COUNTRIES_BASE = "https://restcountries.com/v3.1"
REST_COUNTRIES_TIMEOUT_SEC = 10
REST_COUNTRIES_RETRIES = 2

# Scraping
CLARITYPAY_URL = "https://www.claritypay.com"
SCRAPE_TIMEOUT_SEC = 15
SCRAPE_RATE_LIMIT_DELAY_SEC = 1.0
USER_AGENT = "MLE-Hiring-Pipeline/1.0 (educational; rate-limited)"

# Model
DISPUTE_RATE_HIGH_RISK_THRESHOLD = 0.002  # merchants above this are "high dispute risk"
RANDOM_STATE = 42
TEST_SIZE = 0.2

# Portfolio risk
ASSUMED_LOSS_RATE = 0.02  # 2% of volume at risk for high-risk merchants
