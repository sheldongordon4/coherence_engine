from __future__ import annotations
from typing import Literal, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class MetricsResponse(BaseModel):
    coherenceMean: float
    volatilityIndex: float
    predictedDriftRisk: Literal["low", "medium", "high"]
    timestamp: datetime
    windowSec: int
    n: int
    inputs: dict
    meta: dict

class MetricsRecord(BaseModel):
    ts_utc: datetime = Field(..., description="Computation timestamp in UTC")
    window_sec: int
    n: int
    mean: float
    stdev: float
    drift_risk: Literal["low", "medium", "high"]
    source: str = "darshan_api"
    request_id: Optional[str] = None

class StatusResponse(BaseModel):
    status: str
    version: str
    uptime_sec: Optional[float] = None
    start_time: Optional[str] = None
    now: Optional[str] = None
    default_windows: Optional[str] = None
    persistence: Optional[str] = None
    notes: Optional[str] = None

class IngestStatus(BaseModel):
    source: str
    last_ingest_time: datetime | None = None
    last_latency_ms: float | None = None
    last_record_count: int = 0
    pages_fetched: int = 0
    retries: int = 0
