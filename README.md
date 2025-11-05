# Coherence Engine

A lightweight **Data Coherence Engine** that ingests signal data from Darshan’s API (or mock JSON), computes transparent coherence metrics, and exposes them via a **FastAPI** service — with an optional **Streamlit** dashboard for verification.

Enhanced with an **Automation Drift Sentry**, an automation that monitors drift metrics, generates incident reports, and provides a transparent, auditable trail.

---

## Overview

The **Coherence Engine** processes signal summaries from the `/signals/summary` endpoint and computes key metrics that quantify data stability and drift over time.  
It emphasizes **traceability**, **interpretability**, and **modular design** — every computed value can be traced back to its raw input.

### Core Features

- **Data Ingestion:** Fetches data from Darshan’s `/signals/summary` endpoint or mock JSON.
- **Metrics Computation:**
  - `coherenceMean` – rolling average  
  - `volatilityIndex` – standard deviation / mean  
  - `predictedDriftRisk` – rule-based classifier (`low`, `medium`, `high`)
- **API Endpoints:**
  - `GET /coherence/metrics` → current coherence summary  
  - `GET /coherence/predict` → drift risk forecast  
  - `GET /health`, `GET /status` → diagnostics
- **Persistence Layer:** CSV or SQLite for rolling data storage.
- **Streamlit Dashboard:** Visual inspection of coherence metrics.
- **Automation Drift Sentry:** Automated drift detection and incident generation.

---

## Folder Structure

```
coherence_engine/
│
├── .env
├── Makefile
├── requirements.txt
├── rolling_store.csv
│
├── app/
│   ├── __init__.py
│   ├── api.py
│   ├── schemas.py
│   │
│   ├── compute/
│   │   └── metrics.py
│   │
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── csv_store.py
│   │   └── sqlite_store.py
│   │
│   └── ingest/
│       └── darshan_client.py
│
├── automation/
│   ├── __init__.py
│   └── drift_sentry.py
│
├── artifacts/
│   └── incidents/
│       └── (auto-generated JSON drift reports)
│
├── data/
│   └── mock_signals.json
│
├── streamlit_app/
│   ├── app.py
│   └── pages/
│       └── 01_Incidents.py
│
└── tests/
```

---

## Quick Start

### Clone & Setup

```bash
git clone https://github.com/<your-username>/coherence_engine.git
cd coherence_engine
make install
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### Environment Configuration

Create a `.env` file in the root directory:

```bash
DARSHAN_BASE_URL=https://api.darshan.ai/v1
DARSHAN_MODE=mock
MOCK_PATH=/app/data/mock_signals.json
DARSHAN_TIMEOUT_S=5
PERSIST_PATH=/data
DEFAULT_WINDOWS=1h,24h

# Automation configuration
API_BASE=http://localhost:8000
DRIFT_PSI_WARN=0.10
DRIFT_PSI_CRIT=0.25
```

---

### Run the FastAPI Service

```bash
make run
```

or directly:

```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

Test the endpoints:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/coherence/metrics?window=3600
```

---

### Run the Streamlit Dashboard

```bash
make streamlit
```

Or manually:

```bash
API_BASE="http://localhost:8000" streamlit run streamlit_app/app.py
```

In the sidebar, you’ll now see **“Drift Incidents”**, showing all generated incident reports.

---

## Automation Workflow — Drift Sentry

The **Drift Sentry Automation** autonomously monitors drift metrics, compares PSI values to thresholds, and generates timestamped JSON incident reports.

### Run the automation manually

```bash
make automation-drift
```

or

```bash
python -m automation.drift_sentry --window 24h
```

Each run produces a file like:

```
artifacts/incidents/incident_20251030T220045_24h.json
```

Example incident:
```json
{
  "kind": "drift_incident",
  "created_at": "2025-10-30T22:00:45Z",
  "window": "24h",
  "assessment": [
    {"signal": "sensor_A", "metric": "psi", "value": 0.27, "level": "CRITICAL"}
  ],
  "automation": {"name": "drift_sentry", "version": "0.1.0"}
}
```

### Key Benefits
- **Zero core changes:** uses existing FastAPI endpoints as its tools  
- **Auditable:** every decision saved in an incident file  
- **Composable:** ready for CI/CD or cron integration  
- **Streamlit integration:** auto-discovers new incidents  

---

## Example API Output

Example `/coherence/metrics` response:
```json
{
  "coherenceMean": 86.0,
  "volatilityIndex": 0.14,
  "predictedDriftRisk": "low",
  "timestamp": "2025-10-28T17:43:00Z",
  "windowSec": 86400,
  "n": 120,
  "meta": {
    "method": "rolling mean/stdev",
    "latency_ms": 1.2
  }
}
```

---

## Testing

Run all tests:
```bash
make test
```

Or directly:
```bash
pytest -v
```

---

## Makefile Commands

| Command | Description |
|----------|-------------|
| `make install` | Create virtual environment & install dependencies |
| `make run` | Launch FastAPI server |
| `make test` | Run tests |
| `make lint` | Run Pylint & Black checks |
| `make format` | Auto-format code |
| `make streamlit` | Run the Streamlit dashboard |
| `make automation-drift` | Run the Drift Sentry automation |
| `make clean` | Remove virtual environment & artifacts |

---

## Architecture Summary

| Layer | Description |
|--------|--------------|
| **Ingestion** | Pulls data from Darshan API or local mock |
| **Compute** | Calculates mean, volatility, PSI/KS |
| **Persistence** | Stores results in CSV or SQLite |
| **API** | Exposes `/metrics`, `/status`, `/health` |
| **Streamlit** | Visual interface for coherence metrics & incidents |
| **Automation Layer** | Drift Sentry automation monitors metrics and logs drift |

---

## License

MIT License © 2025  
Coherence Engine Project — Developed by Sheldon H. Gordon

---

**Version:** 0.1.0  
**Last Updated:** November 4, 2025  
