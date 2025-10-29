"""
Data Coherence Engine v0.1
FastAPI service to ingest Darshan's /signals/summary, compute metrics, and expose JSON endpoints.

Core tasks implemented:
1) Ingest & process data (Darshan API or mock JSON file)
2) Compute coherenceMean (rolling average), volatilityIndex (stdev/mean), predictedDriftRisk (rule-based)
3) Expose endpoints:
   - GET /health
   - GET /coherence/metrics  -> latest window metrics
   - GET /coherence/predict  -> drift risk forecast (same as metrics for v0.1; placeholder for future model)
4) Optional persistence: CSV or SQLite (toggle via env)
5) Optional Streamlit app provided in separate file (see bottom of file for inline content)

Run locally:
  pip install -r requirements.txt
  export DARSHAN_BASE_URL="https://api.example.com"
  export DARSHAN_API_KEY="<token>"
  uvicorn app:app --reload --port 8000

Mock mode (no external API):
  export MOCK_PATH="./sample_summary.json"  # file with a list of summary rows

Example request:
  curl "http://localhost:8000/coherence/metrics?window=3600&signal=coherenceScore"

Repo tips:
- A new branch must be created for each new feature and deleted after the pull request is reviewed and merged.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

APP_VERSION = os.getenv("ENGINE_VERSION", "0.1.0")
DEFAULT_WINDOW_SEC = int(os.getenv("DEFAULT_WINDOW_SEC", "3600"))  # 1h
PSI_THRESH_LOW = float(os.getenv("PSI_THRESH_LOW", "0.1"))  # reserved for future
PSI_THRESH_MED = float(os.getenv("PSI_THRESH_MED", "0.25"))  # reserved for future
KS_ALPHA = float(os.getenv("KS_ALPHA", "0.05"))  # reserved for future

DARSHAN_BASE_URL = os.getenv("DARSHAN_BASE_URL", "")
DARSHAN_API_KEY = os.getenv("DARSHAN_API_KEY", "")
DARSHAN_TIMEOUT_S = float(os.getenv("DARSHAN_TIMEOUT_S", "10"))
DARSHAN_PAGE_SIZE = int(os.getenv("DARSHAN_PAGE_SIZE", "1000"))

MOCK_PATH = os.getenv("MOCK_PATH")  # if set, use mock JSON instead of live API

PERSISTENCE = os.getenv("PERSISTENCE", "none")  # one of: none, csv, sqlite
CSV_PATH = os.getenv("CSV_PATH", "./rolling_store.csv")
SQLITE_PATH = os.getenv("SQLITE_PATH", "./rolling_store.db")

app = FastAPI(title="Data Coherence Engine", version=APP_VERSION)


class MetricsResponse(BaseModel):
    coherenceMean: float
    volatilityIndex: float
    predictedDriftRisk: str
    timestamp: datetime
    windowSec: int
    n: int
    inputs: Dict[str, Any]
    meta: Dict[str, Any]


@dataclass
class SummaryRow:
    timestamp: datetime
    coherenceScore: float
    agentStates: Dict[str, Any]
    eventCount: int


# ------------------------------- Ingest Layer ------------------------------- #

def parse_timestamp(ts: str | int | float) -> datetime:
    """Parse ISO8601 or epoch seconds to timezone-aware UTC datetime."""
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    # assume ISO8601
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_mock_summary(path: str) -> List[SummaryRow]:
    with open(path, "r") as f:
        data = json.load(f)
    # allow single dict or list of dicts
    rows = data if isinstance(data, list) else [data]
    out: List[SummaryRow] = []
    for r in rows:
        out.append(
            SummaryRow(
                timestamp=parse_timestamp(r["timestamp"]),
                coherenceScore=float(r.get("coherenceScore", r.get("coherence_score", 0.0))),
                agentStates=r.get("agentStates", {}),
                eventCount=int(r.get("eventCount", r.get("events", 0))),
            )
        )
    return out


async def fetch_darshan_summary(
    client: httpx.AsyncClient,
    since: datetime,
    until: datetime,
) -> List[SummaryRow]:
    if not DARSHAN_BASE_URL:
        raise RuntimeError("DARSHAN_BASE_URL not configured; set MOCK_PATH or provide base URL.")

    headers = {}
    if DARSHAN_API_KEY:
        headers["Authorization"] = f"Bearer {DARSHAN_API_KEY}"

    params = {
        "page_size": DARSHAN_PAGE_SIZE,
        "since": since.isoformat(),
        "until": until.isoformat(),
    }

    url = f"{DARSHAN_BASE_URL.rstrip('/')}/signals/summary"

    rows: List[SummaryRow] = []
    next_page: Optional[str] = None

    for _ in range(10):  # hard cap to avoid infinite loops
        p = params.copy()
        if next_page:
            p["page"] = next_page
        resp = await client.get(url, headers=headers, params=p, timeout=DARSHAN_TIMEOUT_S)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=f"Darshan API error: {resp.text}")
        payload = resp.json()
        items = payload.get("items") or payload.get("data") or []
        for r in items:
            try:
                rows.append(
                    SummaryRow(
                        timestamp=parse_timestamp(r["timestamp"]),
                        coherenceScore=float(r.get("coherenceScore", r.get("coherence_score", 0.0))),
                        agentStates=r.get("agentStates", {}),
                        eventCount=int(r.get("eventCount", r.get("events", 0))),
                    )
                )
            except Exception:
                # skip bad rows in v0.1; could log in prod
                continue
        next_page = payload.get("next_page") or payload.get("next")
        if not next_page:
            break

    return rows


async def ingest_window(window_sec: int) -> List[SummaryRow]:
    """Load summary rows for the last window_sec from Darshan or mock file."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(seconds=window_sec)

    if MOCK_PATH:
        rows = load_mock_summary(MOCK_PATH)
        return [r for r in rows if start <= r.timestamp <= end]

    async with httpx.AsyncClient() as client:
        return await fetch_darshan_summary(client, start, end)


# ---------------------------- Compute/Analytics ---------------------------- #

def compute_basic_metrics(rows: List[SummaryRow]) -> Tuple[float, float, int]:
    """Return (coherenceMean, volatilityIndex, n). volatilityIndex = stdev/mean."""
    if not rows:
        return (float("nan"), float("nan"), 0)
    values = [r.coherenceScore for r in rows if r.coherenceScore is not None]
    n = len(values)
    if n == 0:
        return (float("nan"), float("nan"), 0)
    mean_val = float(np.mean(values))
    # sample stdev; guard for n<2
    if n > 1:
        stdev = float(np.std(values, ddof=1))
    else:
        stdev = 0.0
    volatility_index = float(stdev / mean_val) if mean_val != 0 else float("inf")
    return (mean_val, volatility_index, n)


def classify_drift_risk(coherence_mean: float, volatility_index: float) -> str:
    """Simple, transparent rule-based classifier for drift risk.

    Rules (v0.1):
      - HIGH if volatility_index > 0.25 or coherence_mean < 60
      - MEDIUM if 0.10 < volatility_index <= 0.25 or 60 <= coherence_mean < 80
      - else LOW
    """
    if math.isnan(coherence_mean) or math.isnan(volatility_index):
        return "unknown"
    if volatility_index > 0.25 or coherence_mean < 60:
        return "high"
    if (0.10 < volatility_index <= 0.25) or (60 <= coherence_mean < 80):
        return "medium"
    return "low"


# ------------------------------- Persistence ------------------------------- #

def persist_csv(ts: datetime, mean_v: float, vol_idx: float, risk: str, n: int, window_sec: int) -> None:
    row = {
        "timestamp": ts.isoformat(),
        "coherenceMean": mean_v,
        "volatilityIndex": vol_idx,
        "predictedDriftRisk": risk,
        "n": n,
        "windowSec": window_sec,
    }
    header = not os.path.exists(CSV_PATH)
    df = pd.DataFrame([row])
    df.to_csv(CSV_PATH, mode="a", index=False, header=header)


def persist_sqlite(ts: datetime, mean_v: float, vol_idx: float, risk: str, n: int, window_sec: int) -> None:
    conn = sqlite3.connect(SQLITE_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS rolling_metrics (timestamp TEXT, coherenceMean REAL, volatilityIndex REAL, predictedDriftRisk TEXT, n INTEGER, windowSec INTEGER)"
        )
        cur.execute(
            "INSERT INTO rolling_metrics VALUES (?,?,?,?,?,?)",
            (ts.isoformat(), mean_v, vol_idx, risk, n, window_sec),
        )
        conn.commit()
    finally:
        conn.close()


# -------------------------------- Endpoints -------------------------------- #

@app.get("/health")
async def health():
    return {"status": "ok", "version": APP_VERSION}


@app.get("/coherence/metrics", response_model=MetricsResponse)
async def get_coherence_metrics(
    window: int = Query(DEFAULT_WINDOW_SEC, ge=60, le=7 * 24 * 3600),
    signal: str = Query("coherenceScore"),  # reserved for future multi-signal
):
    rows = await ingest_window(window)
    mean_v, vol_idx, n = compute_basic_metrics(rows)

    ts = datetime.now(timezone.utc)
    risk = classify_drift_risk(mean_v, vol_idx)

    # Optional persistence
    if PERSISTENCE == "csv":
        persist_csv(ts, mean_v, vol_idx, risk, n, window)
    elif PERSISTENCE == "sqlite":
        persist_sqlite(ts, mean_v, vol_idx, risk, n, window)

    if n == 0:
        raise HTTPException(status_code=204, detail="No data in window")

    return MetricsResponse(
        coherenceMean=round(mean_v, 4),
        volatilityIndex=round(vol_idx, 6),
        predictedDriftRisk=risk,
        timestamp=ts,
        windowSec=window,
        n=n,
        inputs={
            "signal": signal,
            "source": "mock" if MOCK_PATH else "darshan_api",
        },
        meta={
            "method": "mean/stdev rule-based",
            "latency_ms": 0,  # fill via middleware if needed
        },
    )


@app.get("/coherence/predict")
async def predict_drift(
    window: int = Query(DEFAULT_WINDOW_SEC, ge=60, le=7 * 24 * 3600),
):
    # For v0.1, prediction mirrors current risk computed from the latest window.
    # Placeholder to swap in a forecasting model later.
    rows = await ingest_window(window)
    mean_v, vol_idx, n = compute_basic_metrics(rows)
    ts = datetime.now(timezone.utc)
    risk = classify_drift_risk(mean_v, vol_idx)

    if n == 0:
        raise HTTPException(status_code=204, detail="No data in window")

    return {
        "coherenceMean": round(mean_v, 4),
        "volatilityIndex": round(vol_idx, 6),
        "predictedDriftRisk": risk,
        "timestamp": ts.isoformat(),
        "windowSec": window,
        "n": n,
    }


# ---------------------------- Streamlit (optional) -------------------------- #
STREAMLIT_APP = r"""
# Data Coherence Engine – Verification View

import os
import pandas as pd
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(page_title="Coherence Verification", layout="wide")
st.title("Coherence Verification")

window = st.sidebar.number_input("Window (sec)", min_value=60, max_value=7*24*3600, value=3600, step=60)

if st.button("Fetch Metrics"):
    url = f"{API_BASE}/coherence/metrics?window={window}"
    r = requests.get(url, timeout=15)
    if r.status_code == 200:
        data = r.json()
        st.json(data)
        st.metric("coherenceMean", data["coherenceMean"])
        st.metric("volatilityIndex", data["volatilityIndex"])
        st.metric("predictedDriftRisk", data["predictedDriftRisk"])
    else:
        st.error(f"Error {r.status_code}: {r.text}")
"""

# ------------------------------ Requirements ------------------------------ #
REQUIREMENTS_TXT = """
fastapi==0.114.2
uvicorn[standard]==0.30.6
httpx==0.27.2
pandas==2.2.3
numpy==2.1.2
pydantic==2.9.2
streamlit==1.39.0
"""

# Write helper files on import if not present (dev convenience)
if not os.path.exists("requirements.txt"):
    with open("requirements.txt", "w") as f:
        f.write(REQUIREMENTS_TXT.strip() + "\n")

if not os.path.exists("streamlit_app.py"):
    with open("streamlit_app.py", "w") as f:
        f.write(STREAMLIT_APP)

if MOCK_PATH and not os.path.exists(MOCK_PATH):
    # Create a tiny mock sample if MOCK_PATH is set but file missing
    sample = [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "coherenceScore": 86,
            "agentStates": {"active": 7, "idle": 2},
            "eventCount": 123,
        },
        {
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
            "coherenceScore": 84,
            "agentStates": {"active": 6, "idle": 3},
            "eventCount": 111,
        },
    ]
    with open(MOCK_PATH, "w") as f:
        json.dump(sample, f, indent=2)
