## Mock API Fix Impact Analysis

### 1. Bug description

The mock internal API attempted to generate `internal_risk_flag` using:

- `rng = random.Random(hash(merchant_id))`
- `rng.choice(["low", "medium", "high"], p=[0.6, 0.3, 0.1])`

This has three issues:

- `random.Random.choice()` does **not** accept a probability argument (`p`), so the call is invalid.
- The invalid call was wrapped in a broad `except Exception:` inside `_load_merchant_responses()`, which caused the code to silently fall back to a deterministic pattern instead of failing loudly.
- The RNG was seeded with Python’s built‑in `hash(merchant_id)`, which is intentionally non‑deterministic across processes unless `PYTHONHASHSEED` is fixed.

Because of this, any failure during CSV loading or sampling would trigger a fallback that:

- Assigned `internal_risk_flag` in a repeating pattern `["low", "medium", "high"][i % 3]`.
- Used constant transaction metrics for all merchants (`last_30d_volume=100000`, `txn_count=2000`, `avg_ticket_size=50.0`).

This contaminates the synthetic dataset by:

- Breaking the intended distribution (60% low / 30% medium / 10% high).
- Tying risk flags and metrics to merchant index instead of realistic randomness.
- Encouraging the ML model to pick up artifacts instead of meaningful signals.

### 2. How it was fixed

**a. Stable deterministic seeding**

- Added `stable_seed_from_id(merchant_id: str) -> int` in `apps/mock_api/main.py`:
  - Uses `hashlib.md5(merchant_id.encode()).hexdigest()` and converts to a 32‑bit integer seed.
  - Ensures the same `merchant_id` always produces the same seed across runs and machines.

**b. Correct weighted sampling**

- Replaced the invalid `rng.choice(..., p=[...])` with:
  - `rng.choices(["low", "medium", "high"], weights=[0.6, 0.3, 0.1], k=1)[0]`
- This is the correct Python API for weighted sampling using `random.Random`.

**c. Removal of silent broad exception handling**

- `_load_merchant_responses()` no longer wraps all logic in `except Exception:`.
- New behavior:
  - If `pandas` cannot be imported: log a **warning** and use synthetic fallback data.
  - If `merchants.csv` is missing: log a **warning** and use synthetic fallback data.
  - Any other runtime error (e.g., programming bug in generation logic) is **not** swallowed and will raise normally.

**d. Improved fallback data generation**

- Introduced `_generate_fallback_data()` which:
  - Creates 50 merchants `M001`–`M050`.
  - Uses `stable_seed_from_id(mid)` and a `random.Random` instance per merchant.
  - Generates:
    - `last_30d_txn_count` in a realistic range `[500, 4000]`.
    - `avg_ticket_size` in a realistic range `[20.0, 200.0]`.
    - `last_30d_volume ≈ txn_count * avg_ticket_size * jitter(±10%)`.
    - `internal_risk_flag` via weighted sampling (60% / 30% / 10%).
  - Values are:
    - **Deterministic per merchant_id**.
    - **Varied across merchants**.
    - Maintaining a plausible relationship between volume, transaction count, and average ticket size.

### 3. Distribution of `internal_risk_flag` (before vs after)

From `artifacts/report_context.json` **before** the fix (prior pipeline run):

- `internal_risk_breakdown`:
  - `low`: 16 merchants
  - `medium`: 17 merchants
  - `high`: 17 merchants

This is roughly **balanced (≈ 32% / 34% / 34%)**, not the intended 60/30/10 split and strongly suggests the fallback pattern logic was active or the sampling was effectively broken.

From `artifacts/report_context.json` **after** the fix (current pipeline run):

- `internal_risk_breakdown`:
  - `low`: 24 merchants
  - `medium`: 20 merchants
  - `high`: 6 merchants

This is approximately:

- `low`: 48%
- `medium`: 40%
- `high`: 12%

Given only 50 merchants, this is much closer to the intended **60% / 30% / 10%** distribution and consistent with correct weighted sampling.

### 4. Top predicted high‑risk merchants (before vs after)

**Before (excerpt)** — top 5 by `prob_high_risk`:

- M005 — US — prob ≈ 0.52 — internal_risk_flag = **high**
- M041 — Romania — prob ≈ 0.34 — internal_risk_flag = **high**
- M032 — UK — prob ≈ 0.34 — internal_risk_flag = **high**
- M020 — Portugal — prob ≈ 0.32 — internal_risk_flag = **high**
- M014 — UK — prob ≈ 0.27 — internal_risk_flag = **high**

**After (excerpt)** — top 5 by `prob_high_risk`:

- M032 — UK — prob = 0.45 — internal_risk_flag = **low**
- M027 — UK — prob = 0.42 — internal_risk_flag = **medium**
- M007 — US — prob = 0.38 — internal_risk_flag = **low**
- M004 — UK — prob = 0.30 — internal_risk_flag = **low**
- M018 — Ireland — prob = 0.28 — internal_risk_flag = **medium**

Key changes:

- Prior to the fix, high predicted risk was **strongly aligned** with `internal_risk_flag="high"`.
- After the fix, the top risk merchants have a mix of **low** and **medium** internal risk flags, which is more realistic and indicates the model is no longer simply echoing the synthetic internal flag pattern.

### 5. Feature importance comparison

**Before fix** (top 5 from `feature_importance_ranking`):

1. `internal_risk_flag_encoded` — 1.12  
2. `volume_growth_proxy` — 0.90  
3. `binary_high_internal_flag` — 0.87  
4. `region_encoded` — 0.66  
5. `log_transaction_count` — 0.06  

The model was heavily dominated by **internal_risk_flag_encoded** and **binary_high_internal_flag**, meaning it was largely learning from the synthetic internal flag rather than other behavioral features.

**After fix** (top 5 from `feature_importance_ranking`):

1. `volume_per_transaction` — 0.22  
2. `avg_ticket` — 0.20  
3. `volume_growth_proxy` — 0.13  
4. `region_encoded` — 0.12  
5. `log_transaction_count` — 0.09  

`internal_risk_flag_encoded` and `binary_high_internal_flag` now appear **near the bottom** of the importance list:

- `internal_risk_flag_encoded` ≈ 0.006  
- `binary_high_internal_flag` ≈ 0.005  

Interpretation:

- Before the fix, the model was effectively “over‑trusting” the internal synthetic label.
- After the fix, risk is driven more by transactional structure (volumes, tickets, growth, region), which is healthier for a toy underwriting model.

### 6. Model metric comparison

**Before fix** (from previous `report_context.json`):

- Chosen model: **LogisticRegression**
- `roc_auc`: **0.71**
- `precision`: **0.20**
- `recall`: **0.20**
- `f1`: **0.20**
- `brier_score`: **0.0567**

**After fix** (current `report_context.json`):

- Chosen model: **RandomForest** (LogisticRegression underperforms)
- `roc_auc`: **0.50**
- `precision`: **0.00**
- `recall`: **0.00**
- `f1`: **0.00**
- `brier_score`: **0.0813**

Interpretation:

- The pre‑fix model appeared to have moderately good discrimination (`roc_auc ≈ 0.71`) and non‑trivial precision/recall — but this was strongly influenced by the synthetic, patterned internal risk flags.
- After correcting the mock API, the model’s performance drops to roughly **chance level**:
  - ROC AUC ≈ 0.5, precision/recall/f1 ≈ 0.
  - This is expected given the extremely small dataset (50 merchants) and the removal of artificial internal label structure.
- In other words, the earlier “good” metrics were **not robust**; they relied on artifacts from the mock API bug.

### 7. Portfolio metric comparison

**Before fix**:

- `expected_high_risk_merchants`: **3.54**
- `average_predicted_risk`: **0.0709**
- `expected_loss_proxy`: **≈ 3,947**
- `n_merchants`: 50

**After fix**:

- `expected_high_risk_merchants`: **3.42**
- `average_predicted_risk`: **0.0684**
- `expected_loss_proxy`: **≈ 5,181**
- `n_merchants`: 50

Interpretation:

- The **average predicted risk** and **expected high‑risk count** are similar across runs (as dominated by the tiny dataset and base rates).
- The **expected loss proxy** moves somewhat (≈ \$3.9k → ≈ \$5.2k) but both are illustrative given the assumed 2% loss rate and small portfolio.
- Portfolio‑level conclusions (“moderate portfolio risk”) are broadly similar, but **model confidence is clearly lower** after the fix.

### 8. Other data artifact audit

While reviewing `apps/mock_api/main.py`:

- Transactional fields (`last_30d_volume`, `last_30d_txn_count`, `avg_ticket_size`) are derived from:
  - CSV inputs (`monthly_volume`, `transaction_count`) plus random jitter.
  - No direct dependence on `dispute_rate` or labels — so there is **no obvious target leakage** from the mock API.
- The main artifact risk was:
  - The internal risk flag being both mis‑distributed and patterned in a way that could be trivially learned.
  - Constant fallback transaction metrics across merchants (now fixed).

Larger limitations (left unchanged but documented):

- Very small dataset (50 merchants) makes reliable calibration, feature importance, and threshold setting difficult.
- Out‑of‑fold metrics on such a small sample have high variance and should be treated as **illustrative**, not production‑grade.

### 9. Overall conclusion: were original findings robust?

- **No.** The original “good” model performance (ROC AUC ≈ 0.71 with non‑trivial precision/recall) was **not robust**; it was heavily influenced by the mock API bug:
  - Deterministic, patterned `internal_risk_flag` values tied to merchant index.
  - Overly strong reliance on synthetic internal flags as features.
- After fixing:
  - Internal risk flags follow the intended 60/30/10 distribution (within sampling error).
  - Transactional metrics vary realistically across merchants and remain deterministic per merchant_id.
  - The model’s discrimination drops to around chance, which is **more honest** given the tiny sample and noisy synthetic setup.

In short, the fix makes the synthetic data **more realistic and less artifact‑driven**, but it also reveals that the current underwriting model has limited true signal on this small sample. Any production‑like use would require more data, stronger features, and potentially different model families — but for the purposes of this assignment, the corrected mock API now behaves in a statistically coherent and reproducible way. 

