from pydantic import BaseModel
from typing import Optional

class HealthResponse(BaseModel):
    status: str
    version: str

class StatusResponse(BaseModel):
    status: str
    version: str
    uptime_sec: float
    start_time: str
    now: str
    default_windows: str
    persistence: str
    notes: Optional[str] = None
