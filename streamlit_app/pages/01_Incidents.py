# streamlit_app/pages/01_Incidents.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timezone

import streamlit as st

# --- Config / paths ---
INCIDENTS_DIR = Path("artifacts/incidents")
MODE = os.getenv("COHERENCE_MODE", "demo")
REFRESH_MS = int(os.getenv("UI_REFRESH_MS", "3000"))

# --- Optional auto-refresh (won't error if package missing) ---
try:
    # pip install streamlit-autorefresh (optional)
    from streamlit_autorefresh import st_autorefresh  # type: ignore

    if MODE == "demo":
        st_autorefresh(interval=REFRESH_MS, key="trust_alerts_auto")
except Exception:
    # No autorefresh — safe to continue without it
    pass

st.set_page_config(page_title="Trust Continuity Alerts", layout="wide")

# ==== Helpers (modern caching) ====
@st.cache_data(show_spinner=False)
def list_incident_files(directory: Path) -> List[Path]:
    if not directory.exists():
        return []
    files = sorted(directory.glob("*.json"))
    return files

@st.cache_data(show_spinner=False)
def load_incident(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def load_all_incidents(directory: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for p in list_incident_files(directory):
        obj = load_incident(p)
        if obj:
            items.append(obj)
    return items

def parse_timestamp(ts: str) -> Optional[datetime]:
    try:
        # Support both "timestamp" and older "created_at"
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None

def summarize_alerts(incidents: List[Dict[str, Any]]) -> Tuple[int, int, int, Optional[datetime]]:
    total = 0
    hi = 0
    med = 0
    last_dt: Optional[datetime] = None

    for inc in incidents:
        # Phase-2 schema fields
        risk = (
            inc.get("trustContinuityRisk")
            or inc.get("trustContinuityRiskLevel")
            or inc.get("trustContinuityRisk_level")
        )
        ts = inc.get("timestamp") or inc.get("created_at")
        dt = parse_timestamp(ts) if ts else None

        total += 1
        if isinstance(risk, str):
            r = risk.lower()
            if r == "high":
                hi += 1
            elif r == "medium":
                med += 1

        if dt:
            last_dt = max(last_dt, dt) if last_dt else dt

    return total, hi, med, last_dt

# ==== UI ====
st.title("Trust Continuity Alerts")
st.caption("Ledger-ready incidents emitted by the Coherence Engine. Fields: signalStability, signalLiquidity, trustContinuityRisk, window, trace.")

incidents = load_all_incidents(INCIDENTS_DIR)
total, high, medium, last_dt = summarize_alerts(incidents)

# KPIs
c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2])
with c1:
    st.metric("Total Alerts", total)
with c2:
    st.metric("High", high)
with c3:
    st.metric("Medium", medium)
with c4:
    st.metric("Last Alert (UTC)", last_dt.isoformat().replace("+00:00", "Z") if last_dt else "—")

st.divider()

# Header note per Phase-2 naming
st.markdown("**Labels per Phase-2:** Signal **Stability**, Signal **Liquidity**, **Trust Continuity Risk**.")

if not incidents:
    st.info("No incidents found yet. When incidents are emitted, they will appear here.")
else:
    # Sort newest first by timestamp
    def sort_key(i: Dict[str, Any]) -> float:
        ts = i.get("timestamp") or i.get("created_at")
        dt = parse_timestamp(ts) if ts else None
        return dt.timestamp() if dt else 0.0

    incidents_sorted = sorted(incidents, key=sort_key, reverse=True)

    for inc in incidents_sorted:
        with st.container(border=True):
            event = inc.get("event", "trust_continuity_alert")
            ts = inc.get("timestamp") or inc.get("created_at") or "—"
            window = inc.get("window", "—")
            stability = inc.get("signalStability", inc.get("interactionStability", "—"))
            liquidity = inc.get("signalLiquidity", inc.get("signalVolatility", "—"))
            risk = inc.get("trustContinuityRisk", inc.get("trustContinuityRiskLevel", "—"))
            trace = inc.get("trace", {})

            left, right = st.columns([2, 1])
            with left:
                st.subheader(event.replace("_", " ").title())
                st.write(f"**Timestamp (UTC):** {ts}")
                st.write(f"**Window:** {window}")
                st.write(f"**Signal Stability:** {stability}")
                st.write(f"**Signal Liquidity:** {liquidity}")
                st.write(f"**Trust Continuity Risk:** {risk}")
            with right:
                st.caption("Trace")
                st.json(trace, expanded=False)

    st.divider()
    st.caption(f"Source folder: `{INCIDENTS_DIR}` · Mode: `{MODE}`")
