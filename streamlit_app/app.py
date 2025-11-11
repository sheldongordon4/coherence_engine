# streamlit_app/app.py
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import pandas as pd
import streamlit as st


# ---------------------- Config ----------------------
API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
MODE = os.getenv("COHERENCE_MODE", "demo").strip().lower()
DEFAULT_WINDOW = int(os.getenv("DEFAULT_WINDOW_SEC", "86400"))  # 24h default
REFRESH_SEC = 3 if MODE == "demo" else 15

PAGE_TITLE = "Coherence Operations Console"
st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title("Coherence Operations Console")
st.caption(
    "Signal integrity & trust observability — Phase 2. "
    "Metrics: **Signal Stability**, **Signal Liquidity**, **Trust Continuity Risk**."
)


# ---------------------- Helpers ----------------------
def _get(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def fetch_metrics(window_sec: int, include_legacy: bool = True) -> Optional[Dict[str, Any]]:
    return _get(
        f"{API_BASE}/coherence/metrics",
        params={"window": window_sec, "include_legacy": str(include_legacy).lower()},
    )


def fetch_history(limit: int = 200) -> pd.DataFrame:
    """
    Best-effort history fetch.
    Expects /coherence/history -> List[MetricsRecord] with legacy fields: mean, stdev, drift_risk, ts_utc, window_sec.
    """
    try:
        r = requests.get(f"{API_BASE}/coherence/history", params={"limit": limit}, timeout=10)
        if r.status_code != 200:
            return pd.DataFrame()
        rows = r.json()
        if not isinstance(rows, list):
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        if df.empty:
            return df

        # Normalize columns to Phase-2 names for display
        if "mean" in df.columns:
            df["signalStability"] = pd.to_numeric(df["mean"], errors="coerce")
        if "stdev" in df.columns:
            df["signalLiquidity"] = pd.to_numeric(df["stdev"], errors="coerce")
        if "drift_risk" in df.columns:
            df["trustContinuityRisk"] = df["drift_risk"].astype(str)

        # Parse time
        if "ts_utc" in df.columns:
            df["ts"] = pd.to_datetime(df["ts_utc"], errors="coerce")
        else:
            df["ts"] = pd.NaT

        df = df.sort_values("ts").reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame()


def pct(x: Optional[float]) -> str:
    if x is None:
        return "—"
    return f"{x*100:.1f}%" if x <= 1.0 else f"{x:.1f}"


# ---------------------- Sidebar ----------------------
with st.sidebar:
    st.subheader("Controls")
    preset = st.selectbox("Window", ["1h (3600s)", "6h (21600s)", "24h (86400s)"], index={3600:0,21600:1,86400:2}.get(DEFAULT_WINDOW,2))
    window_map = {"1h (3600s)": 3600, "6h (21600s)": 21600, "24h (86400s)": 86400}
    window_sec = window_map[preset]

    include_legacy = st.checkbox("Include legacy mirrors", value=True)
    st.write(f"**Mode:** `{MODE}`")
    st.write(f"**Auto-refresh:** every `{REFRESH_SEC}s`")
    st.write(f"**API:** `{API_BASE}`")

# Optional auto-refresh (works if streamlit-autorefresh is installed; otherwise no-op)
try:
    from streamlit_autorefresh import st_autorefresh as _auto
    _auto(interval=REFRESH_SEC * 1000, limit=None, key="auto_refresh_main")
except Exception:
    pass


# ---------------------- Data fetch ----------------------
metrics = fetch_metrics(window_sec=window_sec, include_legacy=include_legacy)
history_df = fetch_history(limit=300)


# ---------------------- Guard ----------------------
if not metrics:
    st.error("Could not fetch metrics from the API. Check API_BASE and server status.")
    st.stop()


# ---------------------- KPIs ----------------------
col1, col2, col3, col4 = st.columns(4)

stability = metrics.get("interactionStability")
liquidity = metrics.get("signalVolatility")
risk = (metrics.get("trustContinuityRiskLevel") or "").lower()
trend = metrics.get("coherenceTrend")

risk_emoji = {"low": "🟢", "medium": "🟠", "high": "🔴"}.get(risk, "⚪")

col1.metric("Signal Stability", pct(stability))
col2.metric("Signal Liquidity", f"{liquidity:.4f}" if isinstance(liquidity, (int, float)) else "—")
col3.metric("Trust Continuity Risk", f"{risk_emoji} {risk.title() if risk else '—'}")
col4.metric("Trend", trend or "—")

# Interpretation chips
st.write("**Interpretation**")
interp = metrics.get("interpretation") or {}
c1, c2, c3 = st.columns(3)
c1.success(f"Stability: {interp.get('stability', '—')}")
c2.info(f"Trust Continuity: {interp.get('trustContinuity', '—')}")
c3.info(f"Trend: {interp.get('coherenceTrend', '—')}")


# ---------------------- Charts ----------------------
st.divider()
st.subheader("Signals Over Time")

if not history_df.empty and history_df["ts"].notna().any():
    plot_df = history_df[["ts", "signalStability", "signalLiquidity"]].dropna()
    plot_df = plot_df.set_index("ts")
    st.line_chart(plot_df, height=260)
else:
    st.info("No history available yet. Enable persistence or run the drift sentry to accumulate records.")


# ---------------------- Raw Panels ----------------------
st.divider()
left, right = st.columns(2)

with left:
    st.subheader("Latest Response (JSON)")
    st.json(metrics, expanded=False)

with right:
    st.subheader("Meta")
    meta = metrics.get("meta") or {}
    generated = meta.get("timestamp")
    window_info = meta.get("windowSec", window_sec)
    n = meta.get("n")
    data = {
        "Timestamp (UTC)": generated,
        "Window (sec)": window_info,
        "Samples (n)": n,
        "Method": meta.get("method"),
    }
    st.table(pd.DataFrame(list(data.items()), columns=["Field", "Value"]))


# ---------------------- Footer ----------------------
st.caption(
    "Phase 2 naming: **interactionStability**, **signalVolatility**, **trustContinuityRiskLevel**, **coherenceTrend**. "
    "Use `COHERENCE_MODE=demo|production` to adjust refresh cadence."
)
