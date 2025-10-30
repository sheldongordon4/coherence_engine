# Data Coherence Engine v0.1

## Overview
Build a lightweight **Data Coherence Engine** that:
- Ingests **Darshan’s `/signals/summary` API data** (or a mock JSON for local development).  
- Computes transparent coherence metrics: **mean**, **volatility (stdev)**, and **drift risk (rule-based)**.  
- **Stores rolling data** in a local **CSV or SQLite** database for persistence testing.  
- Serves results via a clean **JSON API (FastAPI)** with an optional **Streamlit verification UI**.  
- Emphasizes **clarity, traceability, and interpretability** — every number can be explained.

---

## Objectives
- Deliver a **stateless JSON service** exposing coherence metrics per signal and time window.  
- Provide **transparent, explainable math** and **human-readable JSON** (with inputs, window, timestamp, and method).  
- Add a **Streamlit verification view** for quick human validation and product checks.  
- Include **rolling persistence** in CSV/SQLite for local retention and testing.  
- Ship with **robust tests**, **structured logging**, and minimal ops friction (**Docker**, `.env`, `Makefile`).  

---

## Scope

### In Scope
- API adapter for **Darshan’s `/signals/summary`** (auth, pagination, retries, backoff).  
- Rolling metrics over user-selectable windows (e.g., `5m`, `1h`, `24h`).  
- **Drift risk classification** using simple rule-based logic (`low`, `medium`, `high`).  
- **FastAPI service** exposing:
  - `/health`
  - `/status`
  - `/coherence/metrics`
  - `/coherence/predict`
- **Persistence layer** storing rolling metrics in **CSV or SQLite** for testing.  
- **Streamlit verification view** showing metrics over time and risk trends.  
- Configuration via environment variables (`.env`), containerized deployment with Docker.

---

## Technology Stack
- **Python 3.11**, **FastAPI** (service), **HTTPX** (ingest), **Pydantic** (schemas), **Pandas/Numpy** (metrics).  
- **Streamlit** (optional verification UI).  
- **SQLite/CSV** (rolling persistence).  
- **Docker + Uvicorn**, **Makefile** for automation tasks.  
- **Pytest** for testing, **Ruff/Black** for lint/format, **structured JSON logging** (OpenTelemetry hooks optional).  

---

## Metrics (clear & explainable)

### Windowing
Fixed or rolling windows based on timestamps from Darshan’s data.  
Default window: **1 hour (3600s)**.

### 1) Mean
μ = (1/n) Σ xᵢ

### 2) Volatility (sample stdev)
σ = √(1/(n−1) Σ (xᵢ − μ)²)

### 3) Drift Risk (Rule-based)
Risk levels are determined by:
- **High:** volatilityIndex > 0.25 or coherenceMean < 60  
- **Medium:** 0.10 < volatilityIndex ≤ 0.25 or 60 ≤ mean < 80  
- **Low:** volatilityIndex ≤ 0.10 and mean ≥ 80  

Each response includes `coherenceMean`, `volatilityIndex`, `predictedDriftRisk`, and metadata about calculation time, source, and window.

---

## API Design (FastAPI)

### Routes
- `GET /health` → `{"status": "ok", "version": "0.1.0"}`  
- `GET /status` → Returns last ingest time, API latency, configured windows.  
- `GET /coherence/metrics?window=1h` → Returns metrics for the latest window.  
- `GET /coherence/predict?window=1h` → Returns drift forecast (same as metrics for v0.1).

### Response Example
```json
{
  "coherenceMean": 86,
  "volatilityIndex": 0.14,
  "predictedDriftRisk": "low",
  "timestamp": "2025-10-29T17:43:00Z",
  "windowSec": 3600,
  "n": 120,
  "inputs": {
    "start_ts": "2025-10-29T16:43:00Z",
    "end_ts": "2025-10-29T17:43:00Z",
    "source": "darshan_api"
  },
  "meta": {
    "method": "mean/stdev rule-based",
    "engine_version": "0.1.0",
    "latency_ms": 38
  }
}
```

---

## Ingestion Adapter (Darshan API)
- **Config:** `DARSHAN_BASE_URL`, `DARSHAN_API_KEY`, `PAGE_SIZE`, `MAX_RETRIES`, `TIMEOUT_S`.  
- **Pull strategy:** time-bounded queries, pagination, deduplication by `(signal, timestamp)`.  
- **Resilience:** exponential backoff and retry on network errors or 5xx responses.  
- **Schema normalization:** `{timestamp, coherenceScore, agentStates, eventCount}` standardized via Pydantic model.  
- **Mock mode:** defined by `MOCK_PATH` for local testing.

---

## Persistence Layer
- **CSV Mode:** Appends computed metrics to `rolling_store.csv`.  
- **SQLite Mode:** Stores metrics in `rolling_store.db` under table `rolling_metrics`.  
- Controlled by `PERSISTENCE` environment variable (`csv`, `sqlite`, or `none`).  
- Enables offline validation and regression testing of rolling metrics.

---

## Streamlit Verification View (optional)
- **Sidebar:** select signal, window, and persistence mode.  
- **Main Panel:**  
  - Time-series plot of coherenceMean and volatility bands.  
  - Risk classification panel (Low / Medium / High).  
  - Table of recent computed values.  
- **Export button:** downloads JSON matching API schema.

---

## Logging & Metrics
- **Structured JSON logs:** include event type, signal, window, mean, volatility, drift risk, latency, and request ID.  
- **Request IDs:** propagate through ingestion and computation layers.  
- **Metrics exposed:** request count, P95 latency, error rate, last ingest time.

---

## Testing
- **Unit Tests:** mean, stdev, and drift-risk classification.  
- **Integration Tests:** mock Darshan API ingestion, FastAPI routes, persistence layer.  
- **Contract Tests:** Pydantic schema validation.  
- **Performance Smoke Tests:** up to 100k records per window under 250ms compute budget.  

---

## Version Control
**Repo Layout**
```
coherence-engine/
  app/
    api.py
    schemas.py
    compute/metrics.py
    ingest/darshan_client.py
    persistence/
      csv_store.py
      sqlite_store.py
  streamlit_app/
    app.py
  tests/
    test_metrics.py
    test_api.py
    test_persistence.py
  Dockerfile
  Makefile
  pyproject.toml
  README.md
  .env.example
```
- **Branching:** a new branch must be created for each new feature and deleted after PR review and merge.  
- **Conventional commits;** PR checks include linting, formatting, and tests.

---

## Documentation
- **README.md:** setup, environment variables, run instructions, sample curl.  
- **FastAPI `/docs`:** auto-generated OpenAPI documentation.  
- **Metrics Explainer:** formulas and thresholds included in repo for transparency.  
- **CHANGELOG:** version history per semantic versioning.

---

## Core Acceptance Criteria
✅ `GET /health` and `/status` respond with version and uptime info.  
✅ `GET /coherence/metrics` computes mean, volatility, and drift risk within **<500ms** for normal data windows.  
✅ Responses include inputs (window bounds, source) and metadata (methods, version, latency).  
✅ Persistence layer (CSV/SQLite) writes metrics successfully.  
✅ Streamlit dashboard renders plots and risk correctly.  
✅ Tests achieve ≥90% coverage for core modules.  
✅ Docker image builds and runs with only `DARSHAN_*` environment variables.

---

## Milestones (compact, high-impact)

### M0 – Project Bootstrap (Day 0–0.5)
Repo initialized with FastAPI skeleton, Makefile, Dockerfile, and lint/test scaffolding.  
**Value:** working service shell; deployable container.

### M1 – Ingestion Adapter (Day 0.5–1.5)
Darshan client with retries, pagination, and time-bounded pulls.  
**Value:** live or mock data flow established.

### M2 – Coherence Metrics (Day 1.5–2.5)
Mean, volatility, and rule-based risk logic implemented.  
**Value:** core analytics operational.

### M3 – Persistence Layer (Day 2.5–3.5)
Rolling data stored in CSV/SQLite; read/write verified.  
**Value:** local retention for QA/testing.

### M4 – Streamlit Verification (Day 3.5–4)
Minimal Streamlit UI for visualization and validation.  
**Value:** human validation and demo readiness.

### M5 – Hardening & Docs (Day 4–5)
Tests, coverage, structured logs, README, examples, final version tag.  
**Value:** shippable, maintainable artifact.

---

## Config (Environment Variables)
```
DARSHAN_BASE_URL
DARSHAN_API_KEY
DARSHAN_TIMEOUT_S=10
DARSHAN_PAGE_SIZE=1000
DEFAULT_WINDOWS=1h,24h
PERSISTENCE=csv | sqlite | none
ENGINE_VERSION=0.1.0
```

---

## Example cURL
```bash
curl "http://localhost:8000/coherence/metrics?window=1h"
```
**Response:**
```json
{
  "coherenceMean": 85.9,
  "volatilityIndex": 0.11,
  "predictedDriftRisk": "medium",
  "timestamp": "2025-10-29T18:43:00Z",
  "n": 3600
}
```
