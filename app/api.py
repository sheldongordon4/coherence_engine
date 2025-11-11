from datetime import datetime, timezone

from fastapi import APIRouter, Query

from .schemas import CoherenceMetricsResponse
from .compute.metrics import compute_metrics

# If you already use a global FastAPI app, you can also do:
# from fastapi import FastAPI
# app = FastAPI()
# and then replace `router` with `app` below.
router = APIRouter()


@router.get("/coherence/metrics", response_model=CoherenceMetricsResponse)
def get_metrics(
    window: int = Query(86400, description="Window in seconds"),
    include_legacy: bool = Query(True, description="Return legacy mirrors in response"),
):
    """
    Returns Phase 2 coherence metrics with the EXACT Updated API field names.

    Response includes:
      interactionStability, signalVolatility, trustContinuityRiskLevel, coherenceTrend,
      interpretation{stability, trustContinuity, coherenceTrend},
      meta{method, windowSec, n, timestamp},
      and legacy mirrors when include_legacy=true.
    """
    # TODO: Replace this with your real loader
    # series = load_series(window)
    # For now, a trivial series to demonstrate shape (replace in your integration).
    series = [0.8, 0.79, 0.81, 0.8, 0.82, 0.8] * max(1, window // 3600)

    payload = compute_metrics(series=series, window_sec=window)

    # Attach a timestamp in meta for audit/ledger friendliness
    payload["meta"]["timestamp"] = datetime.now(timezone.utc).isoformat()

    if not include_legacy:
        payload.pop("coherenceMean", None)
        payload.pop("volatilityIndex", None)
        payload.pop("predictedDriftRisk", None)

    return payload
