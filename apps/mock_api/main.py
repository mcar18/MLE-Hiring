"""
Mock Internal Merchant Risk API (FastAPI).
Satisfies data/simulated_api_contract.json. Pipeline calls this per merchant.
"""
import json
import random
from pathlib import Path

from fastapi import FastAPI, HTTPException

# Contract path relative to project root (run from repo root: uvicorn apps.mock_api.main:app)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONTRACT_PATH = PROJECT_ROOT / "data" / "simulated_api_contract.json"
MERCHANTS_CSV = PROJECT_ROOT / "data" / "merchants.csv"

app = FastAPI(title="Internal Merchant Risk API", version="1.0")

# Build in-memory store of merchant_id -> response (deterministic from CSV for reproducibility)
_merchant_data: dict[str, dict] = {}


def _load_merchant_responses() -> dict[str, dict]:
    """Load or generate per-merchant responses matching the contract."""
    if _merchant_data:
        return _merchant_data
    try:
        import pandas as pd

        df = pd.read_csv(MERCHANTS_CSV)
        for _, row in df.iterrows():
            mid = str(row["merchant_id"])
            vol = float(row["monthly_volume"])
            txn = int(row["transaction_count"])
            # Simulate last_30d as slight variation of monthly
            rng = random.Random(hash(mid))
            last_30d_vol = vol * (0.9 + rng.uniform(0, 0.2))
            last_30d_txn = max(1, int(txn * (0.9 + rng.uniform(0, 0.2))))
            avg_ticket = last_30d_vol / last_30d_txn if last_30d_txn else 0
            risk = rng.choice(["low", "medium", "high"], p=[0.6, 0.3, 0.1])
            _merchant_data[mid] = {
                "merchant_id": mid,
                "internal_risk_flag": risk,
                "transaction_summary": {
                    "last_30d_volume": round(last_30d_vol, 2),
                    "last_30d_txn_count": last_30d_txn,
                    "avg_ticket_size": round(avg_ticket, 2),
                },
                "last_review_date": "2025-01-15",
            }
    except Exception:
        # Fallback: minimal responses for M001, M002, ...
        for i in range(1, 51):
            mid = f"M{i:03d}"
            _merchant_data[mid] = {
                "merchant_id": mid,
                "internal_risk_flag": ["low", "medium", "high"][i % 3],
                "transaction_summary": {
                    "last_30d_volume": 100000,
                    "last_30d_txn_count": 2000,
                    "avg_ticket_size": 50.0,
                },
                "last_review_date": "2025-01-15",
            }
    return _merchant_data


@app.get("/merchants/{merchant_id}")
def get_merchant(merchant_id: str) -> dict:
    """Return internal risk and transaction summary for one merchant (contract-compliant)."""
    data = _load_merchant_responses()
    if merchant_id not in data:
        raise HTTPException(status_code=404, detail=f"Merchant {merchant_id} not found")
    return data[merchant_id]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
