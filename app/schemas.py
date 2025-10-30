from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DarshanSignalSummary(BaseModel):
    timestamp: datetime
    signal_id: str = Field(..., alias="signal_id")
    coherenceScore: float
    agentStates: Dict[str, Any]
    eventCount: int

class DarshanPage(BaseModel):
    data: List[DarshanSignalSummary]
    next_page: Optional[str] = None

class IngestStatus(BaseModel):
    source: str
    last_ingest_time: Optional[datetime] = None
    last_latency_ms: Optional[int] = None
    last_record_count: int = 0
    pages_fetched: int = 0
    retries: int = 0
