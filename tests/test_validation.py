"""Schema validation tests."""
import pandas as pd
import pytest
from pydantic import ValidationError

from src.validation.schemas import CollatedMerchantSchema, MerchantRowSchema
from src.validation.validators import validate_merchant_row, validate_csv_and_filter


def test_merchant_row_schema_valid():
    d = {
        "merchant_id": "M001",
        "name": "Acme",
        "country": "UK",
        "registration_number": "123",
        "monthly_volume": 100_000.0,
        "dispute_count": 2,
        "transaction_count": 1000,
    }
    row = MerchantRowSchema.model_validate(d)
    assert row.merchant_id == "M001"
    assert row.monthly_volume == 100_000


def test_merchant_row_schema_invalid_volume():
    with pytest.raises(ValidationError):
        MerchantRowSchema.model_validate({
            "merchant_id": "M001",
            "name": "Acme",
            "country": "UK",
            "registration_number": None,
            "monthly_volume": -1,
            "dispute_count": 0,
            "transaction_count": 100,
        })


def test_validate_merchant_row_valid():
    row = pd.Series({
        "merchant_id": "M001",
        "name": "Acme",
        "country": "UK",
        "registration_number": "",
        "monthly_volume": 50_000,
        "dispute_count": 1,
        "transaction_count": 500,
    })
    ok, err = validate_merchant_row(row)
    assert ok is True
    assert err is None


def test_validate_merchant_row_invalid():
    row = pd.Series({
        "merchant_id": "M001",
        "name": "Acme",
        "country": "UK",
        "registration_number": None,
        "monthly_volume": -100,
        "dispute_count": 0,
        "transaction_count": 100,
    })
    ok, err = validate_merchant_row(row)
    assert ok is False
    assert err is not None


def test_validate_csv_and_filter_rejects_bad_rows():
    df = pd.DataFrame([
        {"merchant_id": "M1", "name": "A", "country": "UK", "registration_number": None, "monthly_volume": 1000, "dispute_count": 0, "transaction_count": 100},
        {"merchant_id": "M2", "name": "B", "country": "US", "registration_number": None, "monthly_volume": -1, "dispute_count": 0, "transaction_count": 50},
    ])
    valid_df, errors = validate_csv_and_filter(df)
    assert len(valid_df) == 1
    assert len(errors) == 1
    assert valid_df.iloc[0]["merchant_id"] == "M1"


def test_collated_merchant_schema_valid():
    d = {
        "merchant_id": "M001",
        "country": "UK",
        "monthly_volume": 100_000.0,
        "transaction_count": 1000,
        "dispute_count": 5,
        "dispute_rate": 0.005,
        "avg_ticket": 100.0,
    }
    row = CollatedMerchantSchema.model_validate(d)
    assert row.merchant_id == "M001"
    assert row.dispute_rate == 0.005
