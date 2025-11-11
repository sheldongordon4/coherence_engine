# streamlit_app/pages/01_Incidents.py
import os
import json
import glob
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
import streamlit as st


# ----------------- Config ----------------- #
MODE = os.getenv("COHERENCE_MODE", "demo").strip().lower()
INCIDENT_DIR = os.getenv("INCIDENT_DIR", "artifacts/incidents")

REFRESH_SEC = 3 if MODE == "demo" else 15
st.set_page_config(page_title="Trust Continuity Alerts", layout="wide")


# ----------------- Helpers ----------------- #
def _iso_to_dt(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        # accept either ...Z or +00:00
        s = s.replace("Z", "+00:00") if s.endswith("Z") else s
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _level_color(level: str) -> str:
    lvl = (level or "").lower()
    if lvl == "high":
        return "🔴"
    if lvl == "medium":
        return "🟠"
    return "🟢"


def _read_incident(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        # Expect Phase 2 schema
        return {
            "event": obj.get("event"),
            "timestamp": obj.get("timestamp"),
            "window": obj.get("window"),
            "signalStability": obj.get("signalStability"),
            "signalLiquidity": obj.get("signalLiquidity"),
            "trustContinuityRisk": obj.get("trustContinuityRisk"),
            "trace_source": (obj.get("trace") or {}).get("source"),
            "trace_upstream": (obj.get("trace") or {}).get("upstream"),
            "_raw": obj,
            "_path": path,
        }
    except Exception:
        return None


def load_incidents() -> pd.DataFrame:
    os.makedirs(INCIDENT_DIR, exist_ok=True)
    files = sorted(glob.glob(os.path.join(INCIDENT_DIR, "*.json")))
    rows: List[Dict[str, Any]] = []
    for p in files:
        rec = _read_incident(p)
        if rec:
            rows.append(rec)
    if not rows:
        return pd.DataFrame(
            columns=[
                "event",
                "timestamp",
                "window",
                "signalStability",
                "signalLiquidity",
                "trustContinuityRisk",
                "trace_source",
                "trace_upstream",
                "_raw",
                "_path",
            ]
        )
    df = pd.DataFrame(rows)
    # enrich
    df["dt"] = df["timestamp"].apply(_iso_to_dt)
    df["risk_icon"] = df["trustContinuityRisk"].apply(_level_color)
    df = df.sort_values("dt").reset_index(drop=True)
    return df


# ----------------- UI ----------------- #
st.title("Trust Continuity Alerts")
st.caption(
    "Ledger-ready incidents emitted by the Coherence Engine. "
    "Fields: signalStability, signalLiquidity, trustContinuityRisk, window, trace."
)

# Auto-refresh note
st.sidebar.write(f"**Mode:** `{MODE}`")
st.sidebar.write(f"**Auto-refresh:** every `{REFRESH_SEC}s`")
st.sidebar.write(f"**Incident dir:** `{INCIDENT_DIR}`")

# Filters
df = load_incidents()
all_windows = sorted([w for w in df["window"].dropna().unique().tolist()]) if not df.empty else []
all_levels = ["low", "medium", "high"]

with st.sidebar:
    risk_sel = st.multiselect("Risk level", all_levels, default=all_levels)
    win_sel = st.multiselect("Window", all_windows, default=all_windows)

# Apply filters
if not df.empty:
    if risk_sel:
        df = df[df["trustContinuityRisk"].str.lower().isin([r.lower() for r in risk_sel])]
    if win_sel:
        df = df[df["window"].isin(win_sel)]

# KPIs
col1, col2, col3, col4 = st.columns(4)
total = len(df)
high_ct = int((df["trustContinuityRisk"].str.lower() == "high").sum()) if total else 0
med_ct = int((df["trustContinuityRisk"].str.lower() == "medium").sum()) if total else 0
low_ct = int((df["trustContinuityRisk"].str.lower() == "low").sum()) if total else 0
last_ts = df["dt"].max().isoformat() if total and df["dt"].notna().any() else "—"

col1.metric("Total Alerts", total)
col2.metric("High", high_ct)
col3.metric("Medium", med_ct)
col4.metric("Last Alert (UTC)", last_ts.replace("+00:00", "Z") if last_ts != "—" else "—")

st.divider()

# Table
if df.empty:
    st.info("No incidents found yet. When incidents are emitted, they will appear here.")
else:
    show_cols = [
        "risk_icon",
        "trustContinuityRisk",
        "window",
        "signalStability",
        "signalLiquidity",
        "timestamp",
        "trace_source",
        "trace_upstream",
        "_path",
    ]
    pretty = df[show_cols].rename(
        columns={
            "risk_icon": "",
            "trustContinuityRisk": "Risk",
            "window": "Window",
            "signalStability": "Signal Stability",
            "signalLiquidity": "Signal Liquidity",
            "timestamp": "Timestamp",
            "trace_source": "Source",
            "trace_upstream": "Upstream",
            "_path": "File",
        }
    )
    st.dataframe(
        pretty,
        hide_index=True,
        use_container_width=True,
    )

    # Details expander for the latest incident
    with st.expander("Latest incident details (raw JSON)"):
        latest = df.iloc[-1]
        st.json(latest["_raw"], expanded=False)

    # Download CSV
    csv_bytes = pretty.to_csv(index=False).encode("utf-8")
    st.download_button("Download as CSV", data=csv_bytes, file_name="trust_continuity_alerts.csv", mime="text/csv")

# Footer + auto-refresh
st.caption("Labels per Phase-2: **Signal Stability**, **Signal Liquidity**, **Trust Continuity Risk**.")
st.experimental_singleton.clear()  # no-op safety on older Streamlit; harmless if unsupported
st_autorefresh = st.empty()
st_autorefresh.write(f"Auto-refreshing every **{REFRESH_SEC}s**…")
st.experimental_rerun() if st.runtime.exists() and False else None  # placeholder; we rely on Streamlit's built-in Rerun button

# Use Streamlit native autorefresh if available
try:
    from streamlit_autorefresh import st_autorefresh as _auto
    _auto(interval=REFRESH_SEC * 1000, limit=None, key="auto_refresh_incidents")
except Exception:
    # Fallback: suggest manual refresh
    pass
