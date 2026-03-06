# MLE Take-Home: Merchant Underwriting Pipeline & Risk Report

**Candidates:** Start with **[README_ASSIGNMENT.md](README_ASSIGNMENT.md)** for the full brief, time budget, data sources, and deliverables.

This repo implements a production-style merchant underwriting pipeline: ingestion → validation → feature engineering → risk model → portfolio aggregation → LLM-generated report.

---

## Setup

### 1. Virtual environment

From the project root:

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Mac/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment variables (secrets)

Copy the example env file and add your keys (do not commit `.env`):

```bash
copy .env.example .env
```

Edit `.env`:

- **`OPENAI_API_KEY`** — Optional. If set, the pipeline uses OpenAI to generate the underwriting report. If unset, a deterministic mock report is produced so the pipeline still runs end-to-end.

---

## Running the pipeline

From the project root with the venv activated:

```bash
python scripts/run_pipeline.py
```

This will:

1. Start the mock internal API (FastAPI) in the background.
2. Ingest and validate `data/merchants.csv`.
3. Extract text from `data/sample_merchant_summary.pdf` (async).
4. Scrape claritypay.com (rate-limited, with User-Agent).
5. Call the mock API and REST Countries per merchant and collate one row per merchant.
6. Build features, train a baseline risk model, and compute portfolio metrics.
7. Generate a 1–2 page underwriting report (LLM or mock) and write all artifacts.

Outputs are under **`artifacts/`**:

| Artifact | Description |
|----------|-------------|
| `pdf_text.json` | Extracted PDF text |
| `claritypay_parsed.json` | Scraped value props, partners, stats |
| `collated.parquet` | One row per merchant (all sources merged) |
| `featured.parquet` | Collated + features + predictions |
| `model.pkl` | Trained risk model |
| `portfolio_summary.json` | Expected high-risk count, avg risk, expected loss proxy |
| `report_context.json` | Inputs passed to the LLM |
| `underwriting_report.md` | Generated report |
| `llm_prompt.txt` | Prompt sent to the LLM |
| `llm_response.txt` | Raw LLM response |

---

## Running the mock API alone

If you want to run the internal mock API separately (e.g. for debugging):

```bash
uvicorn apps.mock_api.main:app --host 127.0.0.1 --port 8000
```

- Health: `GET http://127.0.0.1:8000/health`
- Merchant: `GET http://127.0.0.1:8000/merchants/M001`

The contract is defined in `data/simulated_api_contract.json`.

---

## Tests

From the project root with the venv activated:

```bash
python -m pytest tests/ -v
```

Tests cover:

- **test_validation.py** — Pydantic schema validation and CSV row filtering.
- **test_features.py** — Feature builder (divide-by-zero, missing values, encodings).
- **test_model.py** — Target construction and training pipeline (including single-class edge case).

---

## Project structure

```
data/                 # merchants.csv, sample PDF, simulated API contract
src/
  config.py           # Paths and settings
  logging_config.py   # Structured logging
  ingestion/          # CSV, mock API client, REST Countries, PDF async, scraper, collate
  validation/         # Pydantic schemas, validators, jsonschema for API
  features/           # Feature builder
  modeling/           # train_model, predict
  portfolio/          # aggregate_risk
  reporting/          # build_report_context, prompts, llm_client, generate_report
  utils/              # io_utils, retry_utils
apps/
  mock_api/           # FastAPI service satisfying simulated_api_contract.json
scripts/
  run_pipeline.py     # End-to-end pipeline entrypoint
tests/                # pytest: validation, features, model
artifacts/            # Pipeline outputs (gitignored)
```

---

## Data assets

See **[data/README.md](data/README.md)** for a short description of each file in `data/`.

---

## Production notes

- **Idempotency:** In production, make the pipeline idempotent by (1) writing artifacts to paths keyed by run ID or date (e.g. `artifacts/2025-03-05/collated.parquet`), (2) using idempotent writes (e.g. atomic rename or versioned object storage), and (3) skipping or reusing steps when inputs have not changed (e.g. hash of inputs or checkpointing).
- **Secrets:** API keys are read from the environment via `python-dotenv`; never hardcoded. Use `.env.example` to document required variables; `.env` is gitignored.
