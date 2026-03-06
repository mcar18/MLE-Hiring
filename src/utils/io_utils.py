"""
I/O helpers: ensure artifact directories exist, read/write parquet and JSON.
"""
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def ensure_dir(path: Path) -> Path:
    """Create parent directories if needed. Return the path."""
    path = Path(path)
    if path.suffix:
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)
    return path


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    """Save DataFrame to parquet; ensure directory exists."""
    ensure_dir(path)
    df.to_parquet(path, index=False)
    logger.info("Saved parquet: %s (%d rows)", path, len(df))


def load_parquet(path: Path) -> pd.DataFrame:
    """Load parquet file."""
    return pd.read_parquet(path)


def save_json(data: Any, path: Path, indent: int = 2) -> None:
    """Save JSON-serializable data to file."""
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)
    logger.info("Saved JSON: %s", path)


def load_json(path: Path) -> Any:
    """Load JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)
