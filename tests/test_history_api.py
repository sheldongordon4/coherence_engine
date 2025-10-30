import os
from fastapi.testclient import TestClient
from app.api import app

def test_history_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSISTENCE", "csv")
    monkeypatch.setenv("CSV_PATH", (tmp_path/"r.csv").as_posix())

    client = TestClient(app)
    # trigger startup
    client.get("/health")
    # compute & persist once
    _ = client.get("/coherence/metrics?window=1h")
    r = client.get("/coherence/history?limit=5")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1
