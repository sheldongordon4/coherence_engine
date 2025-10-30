# 🧠 Coherence Engine

A lightweight **Data Coherence Engine** that ingests signal data from Darshan’s API (or mock JSON), computes transparent coherence metrics, and exposes them via a **FastAPI** service — with an optional **Streamlit** dashboard for internal verification.

---

## 🚀 Overview

The **Coherence Engine** processes signal summaries from the `/signals/summary` endpoint and computes key metrics that quantify data stability and drift over time.  
It emphasizes **traceability**, **interpretability**, and **modular design** — every computed value can be traced back to its raw input.

### Core Features

- **Data Ingestion:** Pulls data from Darshan’s `/signals/summary` endpoint (or a mock JSON file).
- **Metrics Computation:**
  - `coherenceMean` – rolling average  
  - `volatilityIndex` – standard deviation / mean  
  - `predictedDriftRisk` – simple rule-based classifier (`low`, `medium`, `high`)
- **API Endpoints:**
  - `GET /coherence/metrics` → returns current summary  
  - `GET /coherence/predict` → returns drift risk forecast  
  - `GET /health`, `GET /status` → diagnostics  
- **Persistence Layer:** Local CSV or SQLite for rolling data storage.  
- **Streamlit Dashboard:** Visual verification of coherence metrics over time.

---

## 🧩 Folder Structure

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
│   │   ├── csv_store.py
│   │   ├── base.py
│   │   └── sqlite_store.py
│   │
│   └── ingest/
│       └── darshan_client.py
│
├── data/
│   └── mock_signals.json
│
├── streamlit_app/
│   └── app.py
│
└── tests/
```

---

## ⚙️ Quick Start

### 1️⃣ Clone & Setup

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

### 2️⃣ Environment Configuration

Create a `.env` file in the root (example below):

```bash
DARSHAN_BASE_URL=https://api.darshan.ai/v1
DARSHAN_MODE=mock
MOCK_PATH=/app/data/mock_signals.json
DARSHAN_TIMEOUT_S=5
PERSIST_PATH=/data
DEFAULT_WINDOWS=1h,24h
```

---

### 3️⃣ Run the API

```bash
make run
```

or directly:

```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

Check endpoints:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/coherence/metrics?window=3600
```

---

### 4️⃣ Run the Streamlit Dashboard (Optional)

```bash
make streamlit
```

Or manually:

```bash
API_BASE="http://localhost:8000" streamlit run streamlit_app/app.py
```

---

## 🐳 Docker Usage

### Build the API image

```bash
docker build -t coherence-api --target api .
```

Run the API container:

```bash
docker run --name coherence-api   --env-file .env   -e PERSIST_PATH=/data   -e DARSHAN_MODE=mock   -e MOCK_PATH=/app/data/mock_signals.json   -p 8000:8000   -v "$(pwd)/data:/data"   coherence-api
```

### Build the Streamlit image

```bash
docker build -t coherence-streamlit --target streamlit .
docker run -p 8501:8501   -e API_BASE="http://host.docker.internal:8000"   coherence-streamlit
```

---

## 🧮 Example Output

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

## 🧪 Testing

Run all tests:

```bash
make test
```

Or with `pytest` directly:

```bash
pytest -v
```

---

## 🧰 Makefile Commands

| Command | Description |
|----------|--------------|
| `make install` | Set up the virtual environment and install dependencies |
| `make run` | Run FastAPI locally via Uvicorn |
| `make test` | Run all pytest tests |
| `make lint` | Lint code with Pylint and Black |
| `make format` | Auto-format code with Black |
| `make streamlit` | Run the Streamlit dashboard |
| `make clean` | Remove the virtual environment and temp files |

---

## 🧠 Design Notes

- **Transparency:** Every metric is computed via human-readable formulas; no hidden models.  
- **Traceability:** Each metric result includes the computation method, timestamp, and source.  
- **Resilience:** Ingestion layer supports mock data fallback and retry logic.  
- **Extensibility:** Metrics module and persistence layer are modular and easily replaceable.

---

## 🧾 License

MIT License © 2025 [Your Name or Organization]  
Feel free to fork, extend, or integrate into your own data coherence systems.
