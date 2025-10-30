import os
from fastapi.testclient import TestClient

# Force env for predictable defaults inside the app module import
os.environ.setdefault("DEFAULT_WINDOW", "1h")
os.environ.pop("MOCK_PATH", None)  # avoid file-based mocks in CI

from app.api import app  # noqa: E402

client = TestClient(app)


def test_health_status_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r = client.get("/status")
    assert r.status_code == 200
    body = r.json()
    for k in ["status", "version", "uptime_sec", "start_time", "now", "default_windows", "persistence", "ingest"]:
        assert k in body


def test_coherence_metrics_default_ok():
    r = client.get("/coherence/metrics")
    assert r.status_code == 200
    body = r.json()
    required = [
        "coherenceMean",
        "volatilityIndex",
        "predictedDriftRisk",
        "timestamp",
        "windowSec",
        "n",
        "inputs",
        "meta",
    ]
    for k in required:
        assert k in body
    assert isinstance(body["n"], int) and body["n"] > 0
    assert 0.0 <= body["coherenceMean"] <= 100.0
    assert body["predictedDriftRisk"] in {"low", "medium", "high"}


def test_coherence_metrics_mock_30m():
    r = client.get("/coherence/metrics", params={"window": "30m", "source": "mock"})
    assert r.status_code == 200
    body = r.json()
    assert body["windowSec"] == 1800
    assert body["inputs"]["source"] == "mock"
    assert body["n"] > 0


def test_invalid_window_rejected():
    r = client.get("/coherence/metrics", params={"window": "banana"})
    assert r.status_code == 400
    assert "Invalid window format" in r.text


def test_unknown_source_rejected():
    r = client.get("/coherence/metrics", params={"source": "not_a_source"})
    assert r.status_code == 400
    assert "Unknown source" in r.text

