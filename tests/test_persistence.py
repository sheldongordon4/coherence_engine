from datetime import datetime, timezone
from app.schemas import MetricsRecord
from app.persistence.csv_store import CsvMetricsStore
from app.persistence.sqlite_store import SqliteMetricsStore

def _sample(ts: str = "2025-10-29T18:43:00+00:00") -> MetricsRecord:
    return MetricsRecord(
        ts_utc=datetime.fromisoformat(ts).astimezone(timezone.utc),
        window_sec=3600,
        n=120,
        mean=86.0,
        stdev=0.14,
        drift_risk="low",
        source="test",
        request_id="req-123",
    )

def test_csv_store_roundtrip(tmp_path):
    p = tmp_path / "r.csv"
    store = CsvMetricsStore(p.as_posix())
    store.init()
    store.save(_sample())
    store.save(_sample("2025-10-29T19:43:00+00:00"))
    rows = store.read_latest(limit=10)
    assert len(rows) == 2
    assert rows[-1].ts_utc.isoformat().startswith("2025-10-29T19:43:00")
    assert rows[-1].drift_risk == "low"

def test_sqlite_store_roundtrip(tmp_path):
    p = tmp_path / "r.db"
    store = SqliteMetricsStore(p.as_posix())
    store.init()
    store.save(_sample())
    store.save(_sample("2025-10-29T19:43:00+00:00"))
    rows = store.read_latest(limit=10)
    assert len(rows) == 2
    # sqlite returns DESC; latest first
    assert rows[0].ts_utc.isoformat().startswith("2025-10-29T19:43:00")
    assert rows[1].ts_utc.isoformat().startswith("2025-10-29T18:43:00")

