"""
Pydantic schemas for CSV and collated data validation.
Ensures governance: reject malformed rows and log errors.
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MerchantRowSchema(BaseModel):
    """Schema for one row of merchants.csv. Validate before use."""

    merchant_id: str = Field(..., min_length=1, description="e.g. M001")
    name: str = Field(..., min_length=1)
    country: str = Field(..., min_length=1)
    registration_number: Optional[str] = None
    monthly_volume: float = Field(..., ge=0)
    dispute_count: int = Field(..., ge=0)
    transaction_count: int = Field(..., ge=0)

    model_config = ConfigDict(str_strip_whitespace=True)


class CollatedMerchantSchema(BaseModel):
    """Schema for one row of the collated underwriting dataset (one row per merchant)."""

    merchant_id: str = Field(..., min_length=1)
    country: str = Field(..., min_length=1)
    monthly_volume: float = Field(..., ge=0)
    transaction_count: int = Field(..., ge=0)
    dispute_count: int = Field(..., ge=0)
    dispute_rate: float = Field(..., ge=0, le=1)
    avg_ticket: float = Field(..., ge=0)
    # Enrichment (optional)
    region: Optional[str] = None
    subregion: Optional[str] = None
    country_code: Optional[str] = None
    internal_risk_flag: Optional[str] = None
    last_30d_volume: Optional[float] = None
    last_30d_txn_count: Optional[int] = None
    avg_ticket_size: Optional[float] = None
    last_review_date: Optional[str] = None
    volume_growth_proxy: Optional[float] = None

    model_config = ConfigDict(str_strip_whitespace=True)
