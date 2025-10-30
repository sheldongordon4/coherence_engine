# -----------------------
# Base image (shared deps)
# -----------------------
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# curl for healthcheck; libgomp for numpy/scikit-learn wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Leverage layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Non-root and writable data volume
RUN useradd -m -u 10001 appuser \
 && mkdir -p /data \
 && chown -R appuser:appuser /data /app
VOLUME ["/data"]
USER appuser

# Copy your code (no secrets: .env not copied)
COPY --chown=appuser:appuser app /app/app
COPY --chown=appuser:appuser data /app/data
COPY --chown=appuser:appuser streamlit_app /app/streamlit_app
# If you want to seed an initial CSV inside the image, uncomment next line:
# COPY --chown=appuser:appuser rolling_store.csv /data/rolling_store.csv


# -------------
# API Runtime
# -------------
FROM base AS api

# Your ASGI app = app/api.py → app.api:app
ARG APP_MODULE=app.api:app
ENV APP_MODULE=${APP_MODULE}

# Tunables
ENV PORT=8000 \
    UVICORN_WORKERS=1 \
    UVICORN_LOG_LEVEL=info \
    PERSIST_PATH=/data \
    DARSHAN_MODE=mock \
    MOCK_PATH=/app/data/mock_signals.json

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1:${PORT}/health || exit 1

# Use --env-file at runtime for secrets; don't bake .env into image
CMD ["sh", "-c", "uvicorn ${APP_MODULE} --host 0.0.0.0 --port ${PORT} --workers ${UVICORN_WORKERS} --log-level ${UVICORN_LOG_LEVEL}"]


# -------------------
# Streamlit Runtime
# -------------------
FROM base AS streamlit

# Your Streamlit entry = streamlit_app/app.py
ARG STREAMLIT_MAIN=streamlit_app/app.py
ENV STREAMLIT_MAIN=${STREAMLIT_MAIN} \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    API_BASE=http://host.docker.internal:8000

EXPOSE 8501

CMD ["sh", "-c", "streamlit run ${STREAMLIT_MAIN} --server.address=0.0.0.0 --server.port=${STREAMLIT_SERVER_PORT}"]
