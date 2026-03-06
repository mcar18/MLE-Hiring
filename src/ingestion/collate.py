"""
Collation: merge all sources into one merchant-level dataset (one row per merchant).
Output: artifacts/collated.parquet with merchant_id, country, monthly_volume, transaction_count,
dispute_count, dispute_rate, avg_ticket, plus enrichment from API, scraping, PDF (context only).
"""
import asyncio
import logging
from pathlib import Path

import pandas as pd

from src.config import (
    ARTIFACTS_DIR,
    COLLATED_PARQUET,
    MERCHANTS_CSV,
    MOCK_API_BASE_URL,
)
from src.ingestion.csv_ingest import ingest_merchants_csv
from src.ingestion.mock_api_client import fetch_merchant_from_mock_api
from src.ingestion.rest_countries_client import fetch_country_enrichment
from src.utils.io_utils import save_parquet

logger = logging.getLogger(__name__)


def _safe_divide(n: float, d: float, default: float = 0.0) -> float:
    if d is None or d == 0 or (isinstance(d, float) and pd.isna(d)):
        return default
    return n / d


def collate(
    merchants_df: pd.DataFrame,
    mock_api_base_url: str = MOCK_API_BASE_URL,
) -> pd.DataFrame:
    """
    Build one row per merchant: base from CSV, enrich with mock API and REST Countries.
    Add dispute_rate, avg_ticket, and API fields (last_30d_volume, internal_risk_flag, etc.).
    """
    rows = []
    for _, row in merchants_df.iterrows():
        mid = str(row["merchant_id"])
        country = str(row["country"])
        monthly_volume = float(row["monthly_volume"])
        transaction_count = int(row["transaction_count"])
        dispute_count = int(row["dispute_count"])
        dispute_rate = _safe_divide(dispute_count, transaction_count, 0.0)
        avg_ticket = _safe_divide(monthly_volume, transaction_count, 0.0)

        rec = {
            "merchant_id": mid,
            "country": country,
            "monthly_volume": monthly_volume,
            "transaction_count": transaction_count,
            "dispute_count": dispute_count,
            "dispute_rate": dispute_rate,
            "avg_ticket": avg_ticket,
        }

        # Mock API
        api_data = fetch_merchant_from_mock_api(mid, base_url=mock_api_base_url)
        if api_data:
            rec["internal_risk_flag"] = api_data.get("internal_risk_flag")
            ts = api_data.get("transaction_summary") or {}
            rec["last_30d_volume"] = ts.get("last_30d_volume")
            rec["last_30d_txn_count"] = ts.get("last_30d_txn_count")
            rec["avg_ticket_size"] = ts.get("avg_ticket_size")
            rec["last_review_date"] = api_data.get("last_review_date")
        else:
            rec["internal_risk_flag"] = None
            rec["last_30d_volume"] = None
            rec["last_30d_txn_count"] = None
            rec["avg_ticket_size"] = None
            rec["last_review_date"] = None

        # REST Countries
        enrich = fetch_country_enrichment(country)
        if enrich:
            rec["region"] = enrich.get("region")
            rec["subregion"] = enrich.get("subregion")
            rec["country_code"] = enrich.get("country_code")
        else:
            rec["region"] = None
            rec["subregion"] = None
            rec["country_code"] = None

        rows.append(rec)

    df = pd.DataFrame(rows)
    logger.info("Collated %d merchants", len(df))
    return df


def run_collation_and_save(
    csv_path: Path = MERCHANTS_CSV,
    output_path: Path = COLLATED_PARQUET,
) -> pd.DataFrame:
    """Ingest CSV, collate with APIs, save to parquet. Returns collated DataFrame."""
    merchants_df, _ = ingest_merchants_csv(csv_path)
    df = collate(merchants_df)
    save_parquet(df, output_path)
    return df
