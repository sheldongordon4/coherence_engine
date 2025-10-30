# app/api.py
import os
import random
import json
from datetime import datetime, timezone
from typing import Optional, List, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# --- local imports
from app.schemas import IngestStatus, MetricsResponse
from app.compute.metrics import compute_metrics
from app.schemas import IngestStatus

load_dotenv()

# -------------------------
# FastAPI app + constants
# -------------------------
app = FastAPI()
ENGINE_VERSION = os.getenv("ENGINE_VERSION", "0.1.0")
START_TIME = datetime.now(timezone.utc)

# Support both DEFAULT_WINDOW (singular) and legacy DEFAULT_WINDOWS (first value)
_DEFAULT_WINDOW = os.getenv("DEFAULT_WINDOW")
if not _DEFAULT_WINDOW:
    # fallback to first of DEFAULT_WINDOWS if provided, else 1h
    _DEFAULT_WINDOW = (os.getenv("DEFAULT_WINDOWS", "1h,24h").split(",")[0]).strip() or "1h"

# -------------------------
# Status schema (existing)
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

## -------------------------
# Ingestion bootstrap (lazy)
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
    """
    Lazy init ingestion client (M3 optional). If import fails, keep API running.
    """
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

    # yield control to the app
    yield

    # optional: graceful shutdown hooks here
    _client = None

# initialize app with lifespan
app = FastAPI(lifespan=lifespan)

@app.get("/ingest/run")
async def run_ingest(start_ts: Optional[str] = None, end_ts: Optional[str] = None):
    if _client is None:
        raise HTTPException(status_code=503, detail="Ingestion client unavailable (M3 not wired).")
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

# -------------------------
# Health + Status (existing)
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
        persistence=os.getenv("PERSISTENCE", "none"),
        ingest=_ingest_status,
    )

# -------------------------
# Manual ingest (existing)
# -------------------------
@app.get("/ingest/run")
async def run_ingest(start_ts: Optional[str] = None, end_ts: Optional[str] = None):
    global _ingest_status
    assert _client is not None, "Client not initialized"

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

# -------------------------
# M2: Coherence metrics
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
    """Generate a bounded [0,100] synthetic series."""
    vals = []
    val = center / 100.0  # work in 0..1 then scale
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
                # Fallback if the file exists but is empty / missing the key
                if vals:
                    return vals
            except Exception:
                pass
        # Always provide a non-empty synthetic series as a safe default
        return _mock_series()

    if source == "darshan_api":
        return _mock_series(center=74.0, jitter=0.12)

    raise HTTPException(status_code=400, detail=f"Unknown source '{source}'")

@app.get("/coherence/metrics", response_model=MetricsResponse)
async def get_coherence_metrics(
    window: str = Query(default=_DEFAULT_WINDOW),
    source: str = Query(default="darshan_api"),
):
    window_sec = parse_window(window)
    values = _get_values(source)
    if not values:
        raise HTTPException(status_code=422, detail="No values available for the requested source/window.")
    return compute_metrics(values=values, window_sec=window_sec, source=source)
