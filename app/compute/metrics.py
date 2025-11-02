from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Tuple
import math
import time

@dataclass(frozen=True)
class BasicStats:
    mean: float
    stdev: float  # sample stdev
    n: int

def _mean(xs: Iterable[float]) -> Tuple[float, int]:
    total = 0.0
    n = 0
    for v in xs:
        if v is None:
            continue
        total += float(v)
        n += 1
    if n == 0:
        return 0.0, 0
    return total / n, n

def _stdev(xs: Iterable[float], mean: float, n: int) -> float:
    if n <= 1:
        return 0.0
    sse = 0.0
    for v in xs:
        if v is None:
            continue
        dv = float(v) - mean
        sse += dv * dv
    return math.sqrt(sse / (n - 1))

def basic_stats(values: List[float]) -> BasicStats:
    mu, n = _mean(values)
    sigma = _stdev(values, mu, n)
    return BasicStats(mean=mu, stdev=sigma, n=n)

# Rule-based risk:
def classify_risk(mean: float, vol_idx: float) -> Literal["low","medium","high"]:
    if vol_idx < 0.2:  return "low"
    if vol_idx < 0.5:  return "medium"
    return "high"

def compute_metrics(values: List[float], window_sec: int, source: str = "darshan_api") -> dict:
    t0 = time.perf_counter()
    stats = basic_stats(values)
    if abs(stats.mean) < 1e-12:
        vol_idx = 0.0
    else:
        vol_idx = stats.stdev / abs(stats.mean)
    
    risk = classify_risk(stats.mean, vol_idx)
    latency_ms = round((time.perf_counter() - t0) * 1000, 3)
    
    return {
        "coherenceMean": round(stats.mean, 6),
        "volatilityIndex": round(vol_idx, 6),
        "predictedDriftRisk": risk,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "windowSec": int(window_sec),
        "n": stats.n,
        "inputs": {"source": source},
        "meta": {"method": "mean/stdev rule-based", "latency_ms": latency_ms},
    }

