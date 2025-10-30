import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from app.ingest.darshan_client import DarshanClient
from app.schemas import IngestStatus

load_dotenv()

app = FastAPI()

ENGINE_VERSION = os.getenv("ENGINE_VERSION", "0.1.0")

class StatusResponse(BaseModel):
    status: str
    version: str
    uptime_sec: float
    start_time: str
    now: str
    default_windows: str
    persistence: str
    ingest: IngestStatus

START_TIME = datetime.now(timezone.utc)

# --- Ingestion bootstrap
_client: Optional[DarshanClient] = None
_ingest_status = IngestStatus(
    source="mock" if os.getenv("MOCK_PATH") else "darshan_api",
    last_ingest_time=None,
    last_latency_ms=None,
    last_record_count=0,
    pages_fetched=0,
    retries=0,
)

@app.on_event("startup")
async def on_startup():
    global _client
    _client = DarshanClient(
        base_url=os.getenv("DARSHAN_BASE_URL", "http://localhost:9999"),
        api_key=os.getenv("DARSHAN_API_KEY"),
        timeout_s=int(os.getenv("DARSHAN_TIMEOUT_S", "10")),
        page_size=int(os.getenv("DARSHAN_PAGE_SIZE", "500")),
        mock_path=os.getenv("MOCK_PATH"),
    )

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

# Optional: trigger a manual ingest to test the adapter (simple GET)
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
