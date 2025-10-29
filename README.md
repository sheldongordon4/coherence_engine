# 🧠 Data Coherence Engine v0.1

**Author:** Sheldon H. Gordon  
**Project:** Coherence Protocol – Agentic AI Systems Engineer  
**Purpose:** Build the analytics backbone that computes coherence metrics from Darshan’s `/signals/summary` API and exposes interpretable JSON endpoints.

---

## 🚀 Overview
The **Data Coherence Engine** powers the core analytics of Coherence Protocol’s multi-agent system. It ingests signal summaries, computes coherence and drift metrics, and serves clean JSON for downstream dashboards.

### Core Tasks
1️⃣ **Ingest and Process Data**
- Pull from `/signals/summary` (or use mock JSON for testing).
- Parse fields like `coherenceScore`, `agentStates`, `eventCount`.

2️⃣ **Compute Metrics**
- `coherenceMean` (rolling average)
- `volatilityIndex` (stdev / mean)
- `predictedDriftRisk` (rule-based classifier)

3️⃣ **Expose API Endpoints**
- `GET /coherence/metrics` → returns latest summary JSON
- `GET /coherence/predict` → drift risk forecast

4️⃣ **Optional**
- Streamlit dashboard for verification.
- Local CSV or SQLite persistence.

---

## ⚙️ Tech Stack
| Component | Technology |
|------------|-------------|
| API Service | FastAPI or Flask |
| Data | Pandas, NumPy |
| Rule-based Classifier | Scikit-learn (light usage) |
| Visualization | Streamlit |
| Persistence | CSV or SQLite |
| Containerization | Docker |

---

## 🧩 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/data-coherence-engine.git
cd data-coherence-engine
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🔧 Configuration

Create a `.env` file or export environment variables manually:

```bash
DARSHAN_BASE_URL=https://api.example.com
DARSHAN_API_KEY=<your_token>
DEFAULT_WINDOW_SEC=3600
ENGINE_VERSION=0.1.0
PERSISTENCE=csv      # options: none | csv | sqlite
```

For **mock mode** (no API connection):
```bash
MOCK_PATH=./sample_summary.json
```

---

## ▶️ Run the Service

### Option 1 — Local Development
```bash
uvicorn app:app --reload --port 8000
```
Then open: [http://localhost:8000/docs](http://localhost:8000/docs)

### Option 2 — Docker
```bash
docker build -t data-coherence-engine:0.1 .
docker run -p 8000:8000 --env-file .env data-coherence-engine:0.1
```

---

## 🔍 API Endpoints

### ✅ Health Check
```bash
curl http://localhost:8000/health
```
Response:
```json
{"status": "ok", "version": "0.1.0"}
```

### 📈 Coherence Metrics
```bash
curl "http://localhost:8000/coherence/metrics?window=3600"
```
Response:
```json
{
  "coherenceMean": 86,
  "volatilityIndex": 0.14,
  "predictedDriftRisk": "low",
  "timestamp": "2025-10-28T17:43:00Z"
}
```

### 🔮 Drift Prediction
```bash
curl "http://localhost:8000/coherence/predict"
```

---

## 📊 Optional Streamlit Dashboard
Run a simple verification dashboard:
```bash
API_BASE="http://localhost:8000" streamlit run streamlit_app.py
```
View charts and metrics interactively.

---

## 🧱 Project Structure
```
data-coherence-engine/
├── app.py
├── streamlit_app.py
├── requirements.txt
├── README.md
├── sample_summary.json
├── tests/
│   ├── test_metrics.py
│   └── test_api.py
└── rolling_store.csv (optional)
```

---

## 🧪 Testing
```bash
pytest -v
```

---

## 🧭 Notes
- A **new branch must be created for each new feature** and deleted after PR review and merge.
- Focus: **clarity, interpretability, and trustworthy data** — no overfitting.
- Extendable to PSI, KS drift detection, and model-based risk prediction in later versions.

---

## 📄 License
MIT License © 2025 Sheldon H. Gordon
