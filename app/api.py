import os
import json
import random
from datetime import datetime, timezone
from typing import Optional, List, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from app.schemas import IngestStatus, MetricsResponse, MetricsRecord
from app.compute.metrics import compute_metrics
from app.persistence.csv_store import CsvMetricsStore
from app.persistence.sqlite_store import SqliteMetricsStore

load_dotenv()

# --- add helper ---
def _as_metrics_response(obj) -> "MetricsResponse":
    # works whether compute_metrics returns a dict or a MetricsResponse
    from app.schemas import MetricsResponse as _MR
    if isinstance(obj, _MR):
        return obj
    if isinstance(obj, dict):
        return _MR(**obj)
    # last resort: let pydantic coerce
    return _MR.model_validate(obj)  # pydantic v2-safe

# -------------------------
# Constants / env
# -------------------------
ENGINE_VERSION = os.getenv("ENGINE_VERSION", "0.1.0")
PERSISTENCE = os.getenv("PERSISTENCE", "none")  # csv | sqlite | none
CSV_PATH = os.getenv("CSV_PATH", "rolling_store.csv")
SQLITE_PATH = os.getenv("SQLITE_PATH", "rolling_store.db")
START_TIME = datetime.now(timezone.utc)

# Support DEFAULT_WINDOW (preferred) or first of DEFAULT_WINDOWS
_DEFAULT_WINDOW = os.getenv("DEFAULT_WINDOW")
if not _DEFAULT_WINDOW:
    _DEFAULT_WINDOW = (os.getenv("DEFAULT_WINDOWS", "1h,24h").split(",")[0]).strip() or "1h"

# -------------------------
# Persistence
# -------------------------
if PERSISTENCE == "csv":
    store = CsvMetricsStore(CSV_PATH)
elif PERSISTENCE == "sqlite":
    store = SqliteMetricsStore(SQLITE_PATH)
else:
    store = None

# -------------------------
# Lifespan (lazy ingestion client init)
# -------------------------
_client: Optional[Any] = None
_ingest_status = IngestStatus(
    source="mock" if os.getenv("MOCK_PATH") else "darshan_api",
    last_ingest_time=None,
    last_latency_ms=None,
    last_record_count=0,
    pages_fetched=0,
    retries=0,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client
    try:
        from app.ingest.darshan_client import DarshanClient  # type: ignore
        _client = DarshanClient(
            base_url=os.getenv("DARSHAN_BASE_URL", "http://localhost:9999"),
            api_key=os.getenv("DARSHAN_API_KEY"),
            timeout_s=int(os.getenv("DARSHAN_TIMEOUT_S", "10")),
            page_size=int(os.getenv("DARSHAN_PAGE_SIZE", "500")),
            mock_path=os.getenv("MOCK_PATH"),
        )
    except Exception:
        _client = None

    if store:
        store.init()

    yield

    _client = None

# Single app instance
app = FastAPI(title="Coherence Engine", version=ENGINE_VERSION, lifespan=lifespan)

# -------------------------
# Helpers
# -------------------------
def parse_window(window: str) -> int:
    w = window.strip().lower()
    if w.endswith("s"):
        return int(w[:-1])
    if w.endswith("m"):
        return int(w[:-1]) * 60
    if w.endswith("h"):
        return int(w[:-1]) * 3600
    if w.isdigit():
        return int(w)
    raise HTTPException(status_code=400, detail="Invalid window format. Use 30s, 5m, 1h, etc.")

def _mock_series(n: int = 120, center: float = 82.0, jitter: float = 0.06) -> List[float]:
    vals = []
    val = center / 100.0
    for _ in range(n):
        val += random.uniform(-jitter, jitter) * 0.2
        val = max(0.0, min(1.0, val))
        vals.append(round(val * 100.0, 3))
    return vals

def _load_from_mock_path(path: str) -> List[float]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return [float(v) for v in obj.get("coherenceValues", [])]

def _get_values(source: str) -> List[float]:
    if source == "mock":
        mock_path = os.getenv("MOCK_PATH")
        if mock_path and os.path.exists(mock_path):
            try:
                vals = _load_from_mock_path(mock_path)
                if vals:
                    return vals
            except Exception:
                pass
        return _mock_series()
    if source == "darshan_api":
        # API ingestion placeholder
        return _mock_series(center=74.0, jitter=0.12)
    raise HTTPException(status_code=400, detail=f"Unknown source '{source}'")

# -------------------------
# Schemas for /status
# -------------------------
class StatusResponse(BaseModel):
    status: str
    version: str
    uptime_sec: float
    start_time: str
    now: str
    default_windows: str
    persistence: str
    ingest: IngestStatus

# -------------------------
# Routes
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok", "version": ENGINE_VERSION}

@app.get("/status", response_model=StatusResponse)
def status():
    now = datetime.now(timezone.utc)
    return StatusResponse(
        status="ok",
        version=ENGINE_VERSION,
        uptime_sec=(now - START_TIME).total_seconds(),
        start_time=START_TIME.isoformat(),
        now=now.isoformat(),
        default_windows=os.getenv("DEFAULT_WINDOWS", "1h,24h"),
        persistence=PERSISTENCE if store else "none",
        ingest=_ingest_status,
    )

@app.get("/ingest/run")
async def run_ingest(start_ts: Optional[str] = None, end_ts: Optional[str] = None):
    if _client is None:
        raise HTTPException(status_code=503, detail="Ingestion client unavailable (not initialized).")
    global _ingest_status
    records, meta = await _client.fetch_summary(start_ts=start_ts, end_ts=end_ts)
    _ingest_status = IngestStatus(
        source="mock" if os.getenv("MOCK_PATH") else "darshan_api",
        last_ingest_time=datetime.now(timezone.utc),
        last_latency_ms=meta.get("latency_ms"),
        last_record_count=len(records),
        pages_fetched=meta.get("pages_fetched", 0),
        retries=meta.get("retries", 0),
    )
    return {
        "ok": True,
        "records": len(records),
        "latency_ms": meta.get("latency_ms"),
        "pages_fetched": meta.get("pages_fetched"),
        "retries": meta.get("retries"),
    }

@app.get("/coherence/metrics", response_model=MetricsResponse)
async def get_coherence_metrics(
    window: str = Query(default=_DEFAULT_WINDOW),
    source: str = Query(default="darshan_api"),
):
    window_sec = parse_window(window)
    values = _get_values(source)
    if not values:
        raise HTTPException(status_code=422, detail="No values available for the requested source/window.")

    raw = compute_metrics(values=values, window_sec=window_sec, source=source)
    metrics: MetricsResponse = _as_metrics_response(raw)

    if store:
        rec = MetricsRecord(
            ts_utc=metrics.timestamp,
            window_sec=metrics.windowSec,
            n=metrics.n,
            mean=metrics.coherenceMean,
            stdev=metrics.volatilityIndex,
            drift_risk=metrics.predictedDriftRisk,
            source=metrics.inputs.get("source", "darshan_api"),
            request_id=metrics.meta.get("request_id"),
        )
        print("M3 saving:", rec.model_dump())  # quick log
        store.save(rec)

    return metrics

@app.get("/coherence/history", response_model=List[MetricsRecord])
def coherence_history(limit: int = Query(50, ge=1, le=1000)):
    if not store:
        return []
    return store.read_latest(limit=limit)
