import csv
from pathlib import Path
from typing import List
from datetime import datetime, timezone
from app.schemas import MetricsRecord

_HEADERS = ["ts_utc","window_sec","n","mean","stdev","drift_risk","source","request_id"]

class CsvMetricsStore:
    def __init__(self, path: str = "rolling_store.csv") -> None:
        self.path = Path(path)

    def init(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", newline="") as f:
                csv.writer(f).writerow(_HEADERS)

    def save(self, record: MetricsRecord) -> None:
        self.init()
        row = [
            record.ts_utc.astimezone(timezone.utc).isoformat(),
            record.window_sec,
            record.n,
            f"{record.mean:.12g}",
            f"{record.stdev:.12g}",
            record.drift_risk,
            record.source,
            record.request_id or "",
        ]
        with self.path.open("a", newline="") as f:
            csv.writer(f).writerow(row)

    def read_latest(self, limit: int = 100) -> List[MetricsRecord]:
        self.init()
        with self.path.open("r", newline="") as f:
            rows = list(csv.DictReader(f))
        rows = rows[-limit:] if limit else rows
        out: List[MetricsRecord] = []
        for r in rows:
            out.append(MetricsRecord(
                ts_utc=datetime.fromisoformat(r["ts_utc"]),
                window_sec=int(r["window_sec"]),
                n=int(r["n"]),
                mean=float(r["mean"]),
                stdev=float(r["stdev"]),
                drift_risk=r["drift_risk"],  # type: ignore
                source=r.get("source") or "darshan_api",
                request_id=r.get("request_id") or None,
            ))
        return out
