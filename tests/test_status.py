import pytest
from httpx import AsyncClient, ASGITransport
from app.api import app

@pytest.mark.asyncio
async def test_status_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/status")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    for key in ("uptime_sec", "start_time", "now"):
        assert key in data
