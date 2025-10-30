import os
import json
import time
import sqlite3
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from typing import Optional, Tuple

# --------------------------
# Configuration
# --------------------------
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
PERSISTENCE = os.getenv("PERSISTENCE", "csv")  # csv | sqlite | none

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "rolling_store.csv"
SQLITE_PATH = ROOT / "rolling_store.db"
SQLITE_TABLE = "rolling_metrics"

# --------------------------
# Helpers
# --------------------------
@st.cache_data(ttl=10)
def fetch_json(endpoint: str, params: dict | None = None, api_base: str | None = None):
    try:
        base = (api_base or API_BASE).rstrip("/")
        url = f"{base}/{endpoint.lstrip('/')}"
        r = requests.get(url, params=params or {}, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

TIME_CANDIDATES = ["timestamp", "time", "ts", "created_at", "datetime", "date"]
MEAN_CANDIDATES = ["coherenceMean", "coherence_mean", "mean"]
VOL_CANDIDATES  = ["volatilityIndex", "volatility_index", "volatility", "stdev"]

def _pick_col(cols: list[str], candidates: list[str]) -> Optional[str]:
    lower = {c.lower(): c for c in cols}  # map lower→original
    for name in candidates:
        if name in cols:
            return name
        if name.lower() in lower:
            return lower[name.lower()]
    return None

def load_history(persistence: str) -> Tuple[Optional[pd.DataFrame], dict]:
    """
    Returns (df, info) where df may be None.
    info has keys: path, columns, picked_time, picked_mean, picked_vol
    """
    info = {"path": None, "columns": [], "picked_time": None, "picked_mean": None, "picked_vol": None}

    if persistence == "csv" and CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
        info["path"] = str(CSV_PATH)
    elif persistence == "sqlite" and SQLITE_PATH.exists():
        with sqlite3.connect(SQLITE_PATH) as conn:
            df = pd.read_sql_query(f"SELECT * FROM {SQLITE_TABLE}", conn)
        info["path"] = str(SQLITE_PATH)
    else:
        return None, info

    info["columns"] = list(df.columns)

    # pick columns
    tcol = _pick_col(df.columns.tolist(), TIME_CANDIDATES)
    mcol = _pick_col(df.columns.tolist(), MEAN_CANDIDATES)
    vcol = _pick_col(df.columns.tolist(), VOL_CANDIDATES)

    info["picked_time"] = tcol
    info["picked_mean"] = mcol
    info["picked_vol"]  = vcol

    # try to construct a datetime index
    if tcol is not None:
        df[tcol] = pd.to_datetime(df[tcol], errors="coerce", utc=True)
        df = df.sort_values(tcol)
        df = df.set_index(tcol)
        df.index.name = "timestamp"
    else:
        # try index if it looks like time
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.sort_index()
            df.index.name = "timestamp"
        else:
            # last resort: convert the first column if it parses like time
            first = df.columns[0]
            maybe = pd.to_datetime(df[first], errors="coerce", utc=True)
            if maybe.notna().any():
                df[first] = maybe
                df = df.sort_values(first).set_index(first)
                df.index.name = "timestamp"
            else:
                # no time information; fabricate a monotonic index
                df.index = pd.RangeIndex(start=0, stop=len(df), step=1, name="row")

    # normalize metric names for plotting convenience
    if mcol and "coherenceMean" not in df.columns:
        df.rename(columns={mcol: "coherenceMean"}, inplace=True)
    if vcol and "volatilityIndex" not in df.columns:
        df.rename(columns={vcol: "volatilityIndex"}, inplace=True)

    return df, info

def risk_badge(risk: str):
    colors = {"low": "#16a34a", "medium": "#f59e0b", "high": "#dc2626"}
    color = colors.get(str(risk).lower(), "#6b7280")
    return f"<span style='background:{color};color:white;padding:4px 10px;border-radius:999px;font-weight:600'>{risk}</span>"

# --------------------------
# UI
# --------------------------
st.set_page_config(page_title="Coherence Verification", page_icon="✅", layout="wide")
st.title("✅ Coherence Engine — Streamlit Verification")

with st.sidebar:
    st.subheader("Controls")
    api_base = st.text_input("API Base", value=API_BASE)
    window = st.selectbox("Window", ["5m", "1h", "24h"], index=1)
    persistence = st.selectbox("Persistence", ["csv", "sqlite", "none"], index=0)
    refresh = st.button("🔄 Refresh")

# --- Health & Status ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("Health")
    data = fetch_json("health", api_base=api_base) if not refresh else fetch_json.clear() or fetch_json("health", api_base=api_base)
    st.json(data)
with col2:
    st.subheader("Status")
    data = fetch_json("status", api_base=api_base) if not refresh else fetch_json.clear() or fetch_json("status", api_base=api_base)
    st.json(data)

st.divider()

# --- Metrics ---
st.subheader("Latest Metrics")
metrics = (
    fetch_json("coherence/metrics", {"window": window}, api_base=api_base)
    if not refresh else fetch_json.clear() or fetch_json("coherence/metrics", {"window": window}, api_base=api_base)
)

if "error" in metrics:
    st.error(f"Failed to fetch latest metrics: {metrics['error']}")
else:
    cols = st.columns(4)
    cols[0].metric("Mean", f"{metrics.get('coherenceMean', '—')}")
    cols[1].metric("Volatility", f"{metrics.get('volatilityIndex', '—')}")
    cols[2].metric("WindowSec", f"{metrics.get('windowSec', '—')}")
    cols[3].metric("N", f"{metrics.get('n', '—')}")
    st.markdown(
        f"**Risk:** {risk_badge(metrics.get('predictedDriftRisk', 'unknown'))}",
        unsafe_allow_html=True
    )
    st.download_button(
        "⬇️ Download latest JSON",
        data=json.dumps(metrics, indent=2),
        file_name=f"coherence_latest_{window}.json",
        mime="application/json",
        use_container_width=True,
    )

# --- History ---
# --- replace your existing History section with this block ---

st.subheader("Historical View")

df, info = load_history(persistence)
with st.expander("Schema inspector (debug)", expanded=False):
    st.write({"path": info.get("path"), "columns": info.get("columns"),
              "picked_time": info.get("picked_time"),
              "picked_mean": info.get("picked_mean"),
              "picked_vol": info.get("picked_vol")})

if df is None:
    st.info(f"No persisted data found for mode `{persistence}`.")
else:
    # show a peek regardless of schema
    csv_bytes = df.to_csv().encode("utf-8")
    st.download_button(
        "⬇️ Download history (CSV)",
        data=csv_bytes,
        file_name="coherence_history.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # plot if columns exist
    plot_cols = []
    if "coherenceMean" in df.columns:
        st.caption("Coherence Mean over time")
        st.line_chart(df[["coherenceMean"]])
        plot_cols.append("coherenceMean")
    if "volatilityIndex" in df.columns:
        st.caption("Volatility Index over time")
        st.line_chart(df[["volatilityIndex"]])
        plot_cols.append("volatilityIndex")

    if not plot_cols:
        st.warning(
            "Could not find expected metric columns to plot "
            "(looked for any of: "
            f"{MEAN_CANDIDATES} and {VOL_CANDIDATES}). "
            "Use the Schema inspector above to see what's in your store."
        )
