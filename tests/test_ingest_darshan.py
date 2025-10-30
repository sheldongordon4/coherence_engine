import json
import os
import pytest
import pytest_httpx
from httpx import Response

from app.ingest.darshan_client import DarshanClient

@pytest.mark.asyncio
async def test_mock_ingest_reads_file(tmp_path, monkeypatch):
    mock = {
        "data": [
            {
                "timestamp": "2025-10-29T17:00:00Z",
                "signal_id": "s-001",
                "coherenceScore": 90.0,
                "agentStates": {"idle": 1, "active": 9},
                "eventCount": 10
            }
        ],
        "next_page": None
    }
    fp = tmp_path / "mock.json"
    fp.write_text(json.dumps(mock))

    client = DarshanClient(base_url="http://x", api_key=None, mock_path=str(fp))
    records, meta = await client.fetch_summary()
    assert len(records) == 1
    assert meta["pages_fetched"] == 1
    assert meta["retries"] == 0

@pytest.mark.asyncio
async def test_live_ingest_pagination(httpx_mock: pytest_httpx.HTTPXMock):
    page1 = {
        "data": [
            {
                "timestamp": "2025-10-29T17:00:00Z",
                "signal_id": "s-001",
                "coherenceScore": 80.0,
                "agentStates": {"idle": 2},
                "eventCount": 5
            }
        ],
        "next_page": "abc"
    }
    page2 = {
        "data": [
            {
                "timestamp": "2025-10-29T17:05:00Z",
                "signal_id": "s-001",
                "coherenceScore": 82.0,
                "agentStates": {"active": 8},
                "eventCount": 6
            }
        ],
        "next_page": None
    }

    httpx_mock.add_response(
        url="https://api.example.com/v1/signals/summary?page_size=500",
        method="GET",
        json=page1,
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://api.example.com/v1/signals/summary?page_size=500&page=abc",
        method="GET",
        json=page2,
        status_code=200,
    )

    client = DarshanClient(
        base_url="https://api.example.com/v1", api_key="k", timeout_s=2, page_size=500
    )
    records, meta = await client.fetch_summary()
    assert len(records) == 2
    assert meta["pages_fetched"] == 2

