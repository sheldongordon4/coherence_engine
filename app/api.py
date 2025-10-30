import os
import time
from datetime import datetime, timezone
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from .schemas import HealthResponse, StatusResponse

load_dotenv()

ENGINE_VERSION = os.getenv("ENGINE_VERSION", "0.1.0")
DEFAULT_WINDOWS = os.getenv("DEFAULT_WINDOWS", "1h,24h")
PERSISTENCE = os.getenv("PERSISTENCE", "csv")
START_TS = time.time()

class Settings(BaseModel):
    engine_version: str = ENGINE_VERSION
    default_windows: str = DEFAULT_WINDOWS
    persistence: str = PERSISTENCE

settings = Settings()
app = FastAPI(title="Data Coherence Engine", version=settings.engine_version)

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.engine_version)

@app.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    now_ts = time.time()
    uptime = now_ts - START_TS
    start_iso = datetime.fromtimestamp(START_TS, tz=timezone.utc).isoformat()
    now_iso = datetime.fromtimestamp(now_ts, tz=timezone.utc).isoformat()
    return StatusResponse(
        status="ok",
        version=settings.engine_version,
        uptime_sec=round(uptime, 3),
        start_time=start_iso,
        now=now_iso,
        default_windows=settings.default_windows,
        persistence=settings.persistence,
        notes="M0 bootstrap shell; metrics & ingestion arrive in later milestones.",
    )
