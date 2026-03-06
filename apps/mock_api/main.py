"""
Mock Internal Merchant Risk API (FastAPI).
Satisfies data/simulated_api_contract.json. Pipeline calls this per merchant.
"""
import hashlib
import logging
import random
from pathlib import Path

from fastapi import FastAPI, HTTPException

# Contract path relative to project root (run from repo root: uvicorn apps.mock_api.main:app)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONTRACT_PATH = PROJECT_ROOT / "data" / "simulated_api_contract.json"
MERCHANTS_CSV = PROJECT_ROOT / "data" / "merchants.csv"

app = FastAPI(title="Internal Merchant Risk API", version="1.0")
logger = logging.getLogger(__name__)

# Build in-memory store of merchant_id -> response (deterministic from CSV for reproducibility)
_merchant_data: dict[str, dict] = {}


def stable_seed_from_id(merchant_id: str) -> int:
    """Stable per-merchant seed derived from merchant_id (reproducible across runs and machines)."""
    h = hashlib.md5(merchant_id.encode("utf-8")).hexdigest()
    return int(h, 16) % (2**32)


def _generate_fallback_data() -> None:
    """
    Generate synthetic but sensible per-merchant data when CSV / pandas are unavailable.

    Values vary across merchants but are deterministic per merchant_id, and relationships like
    volume ≈ txn_count * avg_ticket_size are preserved.
    """
    for i in range(1, 51):
        mid = f"M{i:03d}"
        seed = stable_seed_from_id(mid)
        rng = random.Random(seed)
        # Reasonable ranges for synthetic data
        last_30d_txn = rng.randint(500, 4000)
        avg_ticket = round(rng.uniform(20.0, 200.0), 2)
        last_30d_vol = round(last_30d_txn * avg_ticket * rng.uniform(0.9, 1.1), 2)
        risk = rng.choices(["low", "medium", "high"], weights=[0.6, 0.3, 0.1], k=1)[0]
        _merchant_data[mid] = {
            "merchant_id": mid,
            "internal_risk_flag": risk,
            "transaction_summary": {
                "last_30d_volume": last_30d_vol,
                "last_30d_txn_count": last_30d_txn,
                "avg_ticket_size": avg_ticket,
            },
            "last_review_date": "2025-01-15",
        }


def _load_merchant_responses() -> dict[str, dict]:
    """Load or generate per-merchant responses matching the contract."""
    if _merchant_data:
        return _merchant_data

    try:
        import pandas as pd
    except ImportError as e:  # pragma: no cover - environment issue, not logic
        logger.warning("pandas not available for mock API (%s); using synthetic fallback data.", e)
        _generate_fallback_data()
        return _merchant_data

    try:
        df = pd.read_csv(MERCHANTS_CSV)
    except FileNotFoundError as e:
        logger.warning("merchants.csv missing for mock API (%s); using synthetic fallback data.", e)
        _generate_fallback_data()
        return _merchant_data

    for _, row in df.iterrows():
        mid = str(row["merchant_id"])
        vol = float(row["monthly_volume"])
        txn = int(row["transaction_count"])
        # Simulate last_30d as slight variation of monthly, seeded stably per merchant
        seed = stable_seed_from_id(mid)
        rng = random.Random(seed)
        last_30d_vol = vol * (0.9 + rng.uniform(0, 0.2))
        last_30d_txn = max(1, int(txn * (0.9 + rng.uniform(0, 0.2))))
        avg_ticket = last_30d_vol / last_30d_txn if last_30d_txn else 0.0
        # Proper weighted sampling: approx 60% low, 30% medium, 10% high
        risk = rng.choices(["low", "medium", "high"], weights=[0.6, 0.3, 0.1], k=1)[0]
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
