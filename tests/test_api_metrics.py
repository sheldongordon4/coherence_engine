import json
from fastapi.testclient import TestClient

from app.api import app  # if you're using a router, import the FastAPI app that mounts it


client = TestClient(app)


def test_metrics_shape_matches_contract():
    r = client.get("/coherence/metrics?window=86400&include_legacy=true")
    assert r.status_code == 200
    body = r.json()

    # Required new fields
    for k in [
        "interactionStability",
        "signalVolatility",
        "trustContinuityRiskLevel",
        "coherenceTrend",
        "interpretation",
        "meta",
    ]:
        assert k in body

    # Types & enums
    assert isinstance(body["interactionStability"], (int, float))
    assert isinstance(body["signalVolatility"], (int, float))
    assert body["trustContinuityRiskLevel"] in {"low", "medium", "high"}
    assert body["coherenceTrend"] in {"Improving", "Steady", "Deteriorating"}

    # Interpretation sub-keys
    interp = body["interpretation"]
    assert set(interp.keys()) == {"stability", "trustContinuity", "coherenceTrend"}
    assert interp["stability"] in {"High", "Medium", "Low"}
    assert interp["trustContinuity"] in {"Stable", "At Risk", "Critical"}
    assert interp["coherenceTrend"] in {"Improving", "Steady", "Deteriorating"}

    # Meta
    meta = body["meta"]
    assert meta["method"] == "rolling mean/stdev; half-window trend"
    assert isinstance(meta["windowSec"], int)
    assert isinstance(meta["n"], int)
    assert isinstance(meta["timestamp"], str)
    assert meta["timestamp"].endswith("Z")

    # Legacy mirrors present
    assert "coherenceMean" in body
    assert "volatilityIndex" in body
    assert "predictedDriftRisk" in body


def test_legacy_fields_removed_when_disabled():
    r = client.get("/coherence/metrics?window=3600&include_legacy=false")
    assert r.status_code == 200
    body = r.json()
    assert "coherenceMean" not in body
    assert "volatilityIndex" not in body
    assert "predictedDriftRisk" not in body


def test_example_response_parses_and_is_consistent():
    """
    Ensures our example file stays consistent with the Pydantic model and contract.
    """
    from app.schemas import CoherenceMetricsResponse

    with open("data/example_response.json", "r", encoding="utf-8") as f:
        ex = json.load(f)

    # Validate with Pydantic model
    model = CoherenceMetricsResponse(**ex)

    # Consistency checks with mirrors
    assert model.coherenceMean == model.interactionStability
    assert model.volatilityIndex == model.signalVolatility
    assert model.predictedDriftRisk == model.trustContinuityRiskLevel
