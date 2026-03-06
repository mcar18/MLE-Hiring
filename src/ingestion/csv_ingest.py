"""
CSV ingestion: load merchants.csv, validate rows with pydantic, reject malformed rows.
"""
import logging
from pathlib import Path

import pandas as pd

from src.validation.validators import validate_csv_and_filter

logger = logging.getLogger(__name__)


def load_merchants_csv(path: Path) -> pd.DataFrame:
    """Load merchants CSV; no validation. Call validate_csv_and_filter after."""
    df = pd.read_csv(path)
    logger.info("Loaded merchants CSV: %s (%d rows)", path, len(df))
    return df


def ingest_merchants_csv(csv_path: Path) -> tuple[pd.DataFrame, list[dict]]:
    """
    Ingest and validate merchants CSV.
    Returns (valid DataFrame, list of validation errors for governance).
    """
    df = load_merchants_csv(csv_path)
    valid_df, errors = validate_csv_and_filter(df)
    if errors:
        logger.warning("CSV ingestion: %d rows rejected due to validation errors", len(errors))
    return valid_df, errors
