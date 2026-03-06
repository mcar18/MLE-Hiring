"""
End-to-end pipeline: ingestion → validation → feature engineering → model → portfolio risk → report.
Run from repo root: python scripts/run_pipeline.py
Produces all artifacts. Starts the mock API in a subprocess so one command runs everything.
"""
import logging
import subprocess
import sys
import time
from pathlib import Path

# Project root on PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import requests

from src.config import (
    ARTIFACTS_DIR,
    CLARITYPAY_ARTIFACT,
    COLLATED_PARQUET,
    FEATURED_PARQUET,
    MOCK_API_BASE_URL,
    PDF_TEXT_JSON,
)
from src.logging_config import setup_logging, get_logger
from src.ingestion.claritypay_scraper import scrape_and_save
from src.ingestion.collate import collate
from src.ingestion.csv_ingest import ingest_merchants_csv
from src.ingestion.pdf_async_ingest import extract_pdf_text_async
from src.features.feature_builder import build_features
from src.modeling.train_model import train_model
from src.modeling.predict import predict_risk
from src.portfolio.aggregate_risk import aggregate_risk, save_portfolio_summary
from src.reporting.generate_report import generate_report
from src.utils.io_utils import save_json

logger = get_logger(__name__)


def start_mock_api() -> subprocess.Popen | None:
    """Start the mock API server in the background. Return process handle or None."""
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "apps.mock_api.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return proc
    except Exception as e:
        logger.warning("Could not start mock API: %s. Ensure uvicorn is installed.", e)
        return None


def wait_for_mock_api(timeout_sec: int = 15) -> bool:
    """Return True when API is ready."""
    url = f"{MOCK_API_BASE_URL}/health"
    for _ in range(timeout_sec):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def run_pipeline() -> None:
    setup_logging()
    logger.info("Starting pipeline")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Start mock API so collation can call it
    proc = start_mock_api()
    if proc:
        if wait_for_mock_api():
            logger.info("Mock API is ready")
        else:
            logger.warning("Mock API did not become ready; collation may fail for API data.")
    else:
        logger.warning("Mock API not started; run manually: uvicorn apps.mock_api.main:app --host 127.0.0.1 --port 8000")

    try:
        # 1) CSV ingestion + validation
        merchants_df, csv_errors = ingest_merchants_csv(PROJECT_ROOT / "data" / "merchants.csv")
        logger.info("CSV: %d valid rows, %d errors", len(merchants_df), len(csv_errors))

        # 2) PDF async
        pdf_result = asyncio.run(extract_pdf_text_async(PROJECT_ROOT / "data" / "sample_merchant_summary.pdf"))
        save_json(pdf_result, PDF_TEXT_JSON)

        # 3) Scrape ClarityPay
        scrape_and_save(CLARITYPAY_ARTIFACT)

        # 4) Collation (calls mock API + REST Countries)
        collated_df = collate(merchants_df)
        collated_df.to_parquet(COLLATED_PARQUET, index=False)
        logger.info("Collated: %s", COLLATED_PARQUET)

        # 5) Feature engineering
        feature_df = build_features(collated_df)

        # 6) Train model
        model, metrics = train_model(feature_df)

        # 7) Predict on full set
        feature_df["prob_high_risk"] = predict_risk(feature_df)

        # 8) Portfolio risk
        portfolio_metrics = aggregate_risk(feature_df, prob_col="prob_high_risk")
        save_portfolio_summary(portfolio_metrics)

        # Save featured dataset (with predictions) for report context
        feature_df.to_parquet(FEATURED_PARQUET, index=False)

        # 9) LLM report
        generate_report(model_metrics=metrics)

        logger.info("Pipeline complete. Artifacts in %s", ARTIFACTS_DIR)
    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=5)


if __name__ == "__main__":
    run_pipeline()
