# ===============================
# Coherence Engine - Dockerfile
# Multi-stage build for API, Streamlit UI, and Agent
# ===============================

# Base image
FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY coherence_engine ./coherence_engine
COPY rolling_store.csv ./rolling_store.csv
COPY .env ./env.example

# Default port for API
EXPOSE 8000

# Stage: API
FROM base AS api
CMD ["uvicorn", "coherence_engine.app.api:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage: Streamlit
FROM base AS streamlit
EXPOSE 8501
ENV API_BASE="http://host.docker.internal:8000"
CMD ["streamlit", "run", "coherence_engine/streamlit_app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# Stage: Automation
FROM base AS automation
# Optional thresholds can be overridden via environment variables
ENV DRIFT_PSI_WARN=0.10 \
    DRIFT_PSI_CRIT=0.25 \
    API_BASE="http://localhost:8000"

CMD ["python", "-m", "coherence_engine.automation.drift_sentry", "--window", "24h"]
