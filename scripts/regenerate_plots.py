"""
Regenerate model plots from existing artifacts.

Useful when plot formatting changes and you don't want to rerun the full pipeline (scraping, etc.).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import FEATURED_PARQUET, REPORT_CONTEXT_JSON
from src.modeling.plots import generate_all_plots


def main() -> None:
    if not FEATURED_PARQUET.exists():
        raise SystemExit(f"Missing {FEATURED_PARQUET}")
    df = pd.read_parquet(FEATURED_PARQUET)

    if "high_risk" in df.columns:
        y_true = df["high_risk"].astype(int).values
    else:
        y_true = (df["dispute_rate"] > 0.002).astype(int).values

    if "prob_high_risk" not in df.columns:
        raise SystemExit("Missing prob_high_risk in featured.parquet")
    y_proba = df["prob_high_risk"].fillna(0).clip(0, 1).values

    if not REPORT_CONTEXT_JSON.exists():
        raise SystemExit(f"Missing {REPORT_CONTEXT_JSON}")
    ctx = json.loads(Path(REPORT_CONTEXT_JSON).read_text(encoding="utf-8"))
    feature_importance = ctx.get("feature_importance_ranking") or []
    feature_importance = [(x[0], float(x[1])) for x in feature_importance]

    generate_all_plots(np.asarray(y_true), np.asarray(y_proba), feature_importance)
    print("Plots regenerated in artifacts/plots/.")  # noqa: T201


if __name__ == "__main__":
    main()

