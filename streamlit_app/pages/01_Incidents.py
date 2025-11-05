import json
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Drift Incidents", layout="wide")

INCIDENT_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "incidents"
INCIDENT_DIR.mkdir(parents=True, exist_ok=True)

st.title("Drift Incidents")
st.caption(f"Directory: {INCIDENT_DIR}")

files = sorted(INCIDENT_DIR.glob("incident_*.json"), reverse=True)
if not files:
    st.info("No incidents found yet. Run the drift agent to generate one:\n\n`make automation-drift`")
    st.stop()

# Summary table
rows = []
for f in files:
    try:
        data = json.loads(f.read_text())
        assess = data.get("assessment", [])
        crit = sum(1 for a in assess if a.get("level") == "CRITICAL")
        warn = sum(1 for a in assess if a.get("level") == "WARN")
        rows.append({
            "file": f.name,
            "created_at": data.get("created_at"),
            "window": data.get("window"),
            "warnings": warn,
            "critical": crit,
        })
    except Exception:
        rows.append({"file": f.name, "created_at": "?", "window": "?", "warnings": "?", "critical": "?"})

st.subheader("Recent Incidents")
st.dataframe(rows, use_container_width=True)

# Details
choice = st.selectbox("Open incident", [r["file"] for r in rows])
selected = INCIDENT_DIR / choice
data = json.loads(selected.read_text())

st.subheader("Incident Details")
col1, col2 = st.columns([1, 2])
with col1:
    st.write({"created_at": data.get("created_at"), "window": data.get("window"), "api_base": data.get("api_base")})
with col2:
    st.json(data.get("agent", {}))

st.divider()
st.subheader("Assessment (signals breaching thresholds)")
assessment = data.get("assessment", [])
if assessment:
    st.dataframe([{k: v for k, v in a.items() if k != "details"} for a in assessment], use_container_width=True)
else:
    st.success("No WARN/CRITICAL signals in this incident.")

st.divider()
with st.expander("Raw JSON (full snapshot)"):
    st.code(selected.read_text(), language="json")

