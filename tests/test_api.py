from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok"
    assert "version" in j

def test_status():
    r = client.get("/status")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok"
    assert "uptime_sec" in j
    assert "default_windows" in j
