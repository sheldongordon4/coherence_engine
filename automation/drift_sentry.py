from __future__ import annotations
import argparse, json, os, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import httpx

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
PSI_WARN = float(os.getenv("DRIFT_PSI_WARN", "0.10"))
PSI_CRIT = float(os.getenv("DRIFT_PSI_CRIT", "0.25"))

# Anchor artifacts inside the repo (coherence_engine/)
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
INCIDENT_DIR = (DEFAULT_ARTIFACT_DIR / "incidents")
INCIDENT_DIR.mkdir(parents=True, exist_ok=True)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def tool_get_metrics(window: str) -> Dict[str, Any]:
    url = f"{API_BASE}/coherence/metrics"
    params = {"window": window}
    with httpx.Client(timeout=15.0) as client:
        r = client.get(url, params=params)
    r.raise_for_status()
    return r.json()

def assess_drift(metrics_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    incidents: List[Dict[str, Any]] = []
    signals = metrics_json.get("signals") or metrics_json.get("data") or []
    for sig in signals:
        name = sig.get("name") or sig.get("signal") or "unknown"
        psi = sig.get("psi")
        if psi is None:
            continue
        level = "CRITICAL" if psi >= PSI_CRIT else "WARN" if psi >= PSI_WARN else None
        if level:
            incidents.append({
                "signal": name,
                "metric": "psi",
                "value": psi,
                "thresholds": {"warn": PSI_WARN, "crit": PSI_CRIT},
                "level": level,
                "details": {k: v for k, v in sig.items() if k not in ("name", "signal")},
            })
    return incidents

def write_incident(window: str, assessment: List[Dict[str, Any]], metrics_ref: Dict[str, Any], out_dir: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    incident_dir = out_dir / "incidents"
    incident_dir.mkdir(parents=True, exist_ok=True)
    path = incident_dir / f"incident_{ts}_{window}.json"
    payload = {
        "kind": "drift_incident",
        "created_at": now_iso(),
        "window": window,
        "api_base": API_BASE,
        "assessment": assessment,
        "metrics_snapshot": metrics_ref,
        "automation": {
            "name": "drift_sentry",
            "version": "0.1.0",
            "policies": {"psi_warn": PSI_WARN, "psi_crit": PSI_CRIT, "acceptance": "No CRITICAL incidents"},
            "budget": {"max_runtime_s": 20, "max_tool_calls": 2},
        },
    }
    path.write_text(json.dumps(payload, indent=2))
    return path

def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal Drift Sentry Automation")
    parser.add_argument("--window", default="24h", help="metrics window, e.g., 1h, 24h")
    parser.add_argument("--fail-on-critical", action="store_true", help="exit non-zero if CRITICAL drift detected")
    parser.add_argument("--out-dir", default=str(DEFAULT_ARTIFACT_DIR), help="base artifacts dir (default: repo ./artifacts)")
    args = parser.parse_args()

    t0 = time.time()
    metrics = tool_get_metrics(args.window)
    assessment = assess_drift(metrics)
    report_path = write_incident(args.window, assessment, metrics, Path(args.out_dir))

    crit = [a for a in assessment if a["level"] == "CRITICAL"]
    warn = [a for a in assessment if a["level"] == "WARN"]
    print(f"[drift_sentry] window={args.window} warnings={len(warn)} critical={len(crit)} "
          f"report={report_path} runtime_s={time.time()-t0:.2f}")

    return 2 if (args.fail_on_critical and crit) else 0

if __name__ == "__main__":
    raise SystemExit(main())
