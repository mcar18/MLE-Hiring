"""Tests for the mock internal Merchant Risk API."""
from __future__ import annotations

import random

import pytest

from apps.mock_api.main import _load_merchant_responses, stable_seed_from_id


def test_stable_seed_from_id_is_deterministic() -> None:
    """Same merchant_id always yields the same seed."""
    s1 = stable_seed_from_id("M001")
    s2 = stable_seed_from_id("M001")
    s3 = stable_seed_from_id("M002")
    assert s1 == s2
    assert s1 != s3


def test_internal_risk_distribution_approximately_matches_weights() -> None:
    """
    Sampling with stable seeds and rng.choices should roughly follow 60/30/10 split.

    We test the sampling logic directly using many synthetic merchant_ids rather than relying on
    the small CSV size.
    """
    flags: list[str] = []
    for i in range(1000):
        mid = f"T{i:04d}"
        seed = stable_seed_from_id(mid)
        rng = random.Random(seed)
        flag = rng.choices(["low", "medium", "high"], weights=[0.6, 0.3, 0.1], k=1)[0]
        flags.append(flag)

    n = len(flags)
    low_share = flags.count("low") / n
    med_share = flags.count("medium") / n
    high_share = flags.count("high") / n

    # Very loose bounds, just to catch obvious regressions
    assert 0.45 <= low_share <= 0.75
    assert 0.15 <= med_share <= 0.45
    assert 0.05 <= high_share <= 0.2


def test_mock_api_responses_are_deterministic_and_vary_across_merchants() -> None:
    """Loaded responses are deterministic across loads and vary across merchant_ids."""
    data1 = _load_merchant_responses().copy()
    # Clear cache and reload to ensure determinism from seeds, not just caching
    from apps.mock_api import main as main_mod

    main_mod._merchant_data.clear()
    data2 = _load_merchant_responses()

    assert data1 == data2

    # Metrics should vary across merchants (no single constant fallback pattern)
    vols = {d["transaction_summary"]["last_30d_volume"] for d in data1.values()}
    txns = {d["transaction_summary"]["last_30d_txn_count"] for d in data1.values()}
    avg_tickets = {d["transaction_summary"]["avg_ticket_size"] for d in data1.values()}
    assert len(vols) > 1
    assert len(txns) > 1
    assert len(avg_tickets) > 1


def test_load_merchant_responses_does_not_silently_swallow_programming_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """If an unexpected error occurs during CSV processing, it should propagate, not silently fall back."""
    import apps.mock_api.main as main_mod

    # Ensure we go through the CSV path (not fallback) by forcing pandas import to succeed
    import pandas as pd

    monkeypatch.setattr(main_mod, "stable_seed_from_id", lambda mid: 123, raising=True)

    # Now patch pandas.read_csv to raise a RuntimeError that is NOT FileNotFoundError
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_csv", boom, raising=True)

    # Clear cache so _load_merchant_responses executes again
    main_mod._merchant_data.clear()

    with pytest.raises(RuntimeError):
        main_mod._load_merchant_responses()

