"""
Drift Sentry — Phase 2
Emits ledger-ready Trust Continuity incidents.

Usage:
  python -m app.agents.drift_sentry --window 24h --output-dir artifacts/incidents --fail-on-critical
  python -m app.agents.drift_sentry --window 3600 --source mock

Environment (optional):
  COHERENCE_MODE=demo|production        # demo uses mock or MOCK_PATH
  DARSHAN_BASE_URL=...                  # if you wire DarshanClient
  DARSHAN_API_KEY=...
  MOCK_PATH=./data/mock_signals.json    # {"coherenceValues": [ ... ]}
  DRIFT_LIQ_WARN=0.10                   # override warning threshold for signal liquidity
  DRIFT_LIQ_CRIT=0.25                   # override critical threshold for signal liquidity
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any

from dotenv import load_dotenv

# Adjust import roots as needed for your project structure
from app.compute.metrics import compute_metrics

# Optional: if you have a client, we attempt to import it; otherwise we stay in demo.
try:
    from app.ingest.darshan_client import DarshanClient  # type: ignore
except Exception:  # pragma: no cover
    DarshanClient = None  # type: ignore


# ------------- helpers ------------- #

def iso_utc_z(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    # Match docs/tests (ends with 'Z')
    return dt.isoformat().replace("+00:00", "Z")


def parse_window_to_seconds(win: str) -> int:
    w = win.strip().lower()
    if w.endswith("s"):
        return int(w[:-1])
    if w.endswith("m"):
        return int(w[:-1]) * 60
    if w.endswith("h"):
        return int(w[:-1]) * 3600
    if w.isdigit():
        return int(w)
    raise ValueError("Invalid window format. Use 30s, 5m, 1h, or seconds.")


def _mock_series(n: int = 120, center_pct: float = 82.0, jitter: float = 0.06) -> List[float]:
    vals: List[float] = []
    val = center_pct / 100.0
    for _ in range(n):
        val += random.uniform(-jitter, jitter) * 0.2
        val = max(0.0, min(1.0, val))
        vals.append(round(val, 4))  # keep [0..1] for stability semantics
    return vals


def _load_from_mock_path(path: str) -> List[float]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    raw = obj.get("coherenceValues", [])
    # normalize to [0..1] if values look like percentages
    if raw and max(raw) > 1.5:
        return [round(float(v) / 100.0, 4) for v in raw]
    return [round(float(v), 4) for v in raw]


def _load_series(window_sec: int, source: str, mode: str) -> Tuple[List[float], str]:
    """
    Returns (series, upstream_label)
    - In demo mode, uses MOCK_PATH or synthetic series.
    - In production, attempts DarshanClient if available, else falls back to demo.
    """
    mock_path = os.getenv("MOCK_PATH")
    if mode == "demo" or source == "mock" or DarshanClient is None:
        if mock_path and os.path.exists(mock_path):
            try:
                return _load_from_mock_path(mock_path), "mock:file"
            except Exception:
                pass
        return _mock_series(n=max(12, min(600, window_sec // 30 or 120))), "mock:synthetic"

    # production path (best-effort)
    try:
        base_url = os.getenv("DARSHAN_BASE_URL", "http://localhost:9999")
        api_key = os.getenv("DARSHAN_API_KEY")
        timeout_s = int(os.getenv("DARSHAN_TIMEOUT_S", "10"))
        page_size = int(os.getenv("DARSHAN_PAGE_SIZE", "500"))

        client = DarshanClient(base_url=base_url, api_key=api_key, timeout_s=timeout_s, page_size=page_size)
        # Replace with your real call that yields a list[float] for the time window.
        # Here, we just fallback until the API shape is finalized.
        # Example:
        # summaries, _meta = await client.fetch_summary(...)
        # series = [s.stability for s in summaries if s.stability is not None]
        # For now, return synthetic with a different center to distinguish:
        return _mock_series(n=max(12, min(600, window_sec // 30 or 120)), center_pct=74.0, jitter=0.12), "darshan:placeholder"
    except Exception:
        return _mock_series(n=max(12, min(600, window_sec // 30 or 120))), "mock:fallback"


def _env_thresholds() -> Tuple[float, float]:
    """
    Liquidity thresholds for incident classification.
    If set, these override the risk label returned by compute_metrics.
    """
    try:
        warn = float(os.getenv("DRIFT_LIQ_WARN", "0.10"))
        crit = float(os.getenv("DRIFT_LIQ_CRIT", "0.25"))
        # ensure sane ordering
        if warn <= 0 or crit <= 0 or crit <= warn:
            raise ValueError
        return warn, crit
    except Exception:
        return 0.10, 0.25


def _risk_from_liquidity(liq: float, warn: float, crit: float) -> str:
    if liq >= crit:
        return "high"
    if liq >= warn:
        return "medium"
    return "low"


def _as_duration_label(window: str | int) -> str:
    if isinstance(window, int):
        # pretty-print e.g., 86400 -> "24h"
        if window % 3600 == 0:
            return f"{window // 3600}h"
        if window % 60 == 0:
            return f"{window // 60}m"
        return f"{window}s"
    return window


# ------------- incident building ------------- #

def build_incident(window_label: str,
                   signal_stability: float,
                   signal_liquidity: float,
                   trust_risk: str,
                   trace_source: str,
                   upstream: str) -> Dict[str, Any]:
    """
    Ledger-ready incident schema (Phase 2):

    {
      "event": "trust_continuity_alert",
      "timestamp": "<iso8601>",
      "window": "<duration>",
      "signalStability": <float>,
      "signalLiquidity": <float>,
      "trustContinuityRisk": "<low|medium|high>",
      "trace": {"source": "...", "upstream": "..."}
    }
    """
    return {
        "event": "trust_continuity_alert",
        "timestamp": iso_utc_z(),
        "window": window_label,
        "signalStability": round(float(signal_stability), 4),
        "signalLiquidity": round(float(signal_liquidity), 4),
        "trustContinuityRisk": trust_risk,
        "trace": {
            "source": trace_source,
            "upstream": upstream,
        },
    }


# ------------- main ------------- #

def main(argv: Optional[List[str]] = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Emit trust continuity incidents for a window.")
    parser.add_argument("--window", type=str, default="24h", help="Window, e.g., 30s, 5m, 1h, 24h, or seconds.")
    parser.add_argument("--output-dir", type=str, default="artifacts/incidents", help="Directory to write incident JSON.")
    parser.add_argument("--source", type=str, default=os.getenv("DEFAULT_SOURCE", "darshan_api"),
                        choices=["darshan_api", "mock"], help="Signal source.")
    parser.add_argument("--fail-on-critical", action="store_true",
                        help="Exit with non-zero code if any critical incident is emitted.")
    parser.add_argument("--quiet", action="store_true", help="Suppress console JSON path output.")

    args = parser.parse_args(argv)

    t0 = time.time()
    mode = os.getenv("COHERENCE_MODE", "demo").strip().lower()
    try:
        window_sec = parse_window_to_seconds(args.window)
    except Exception as e:
        print(f"[drift_sentry] invalid --window: {e}", file=sys.stderr)
        return 2

    # Load series
    series, upstream = _load_series(window_sec, source=args.source, mode=mode)

    # Compute API-level metrics (Phase 2 names)
    payload = compute_metrics(series=series, window_sec=window_sec)

    # Override risk based on env thresholds (optional alignment)
    warn, crit = _env_thresholds()
    effective_risk = _risk_from_liquidity(payload["signalVolatility"], warn, crit)

    # Build incident (ledger-ready schema)
    incident = build_incident(
        window_label=_as_duration_label(args.window),
        signal_stability=payload["interactionStability"],
        signal_liquidity=payload["signalVolatility"],
        trust_risk=effective_risk,
        trace_source=f"coherence_engine_v{os.getenv('ENGINE_VERSION','0.1')}",
        upstream=upstream,
    )

    # Persist incident JSON
    os.makedirs(args.output_dir, exist_ok=True)
    fname = f"incident_{iso_utc_z().replace(':','').replace('-','')}_{_as_duration_label(args.window)}.json"
    fpath = os.path.join(args.output_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(incident, f, ensure_ascii=False, indent=2)

    # Summarize severities
    warnings = 1 if effective_risk == "medium" else 0
    critical = 1 if effective_risk == "high" else 0

    dt = time.time() - t0
    print(
        f"[drift_sentry] window={_as_duration_label(args.window)} "
        f"warnings={warnings} critical={critical} "
        f"report={os.path.abspath(fpath)} runtime_s={dt:.2f}"
    )

    if args.fail_on-critical or args.fail_on_critical:  # guard for both variants seen in history
        return 2 if critical > 0 else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
