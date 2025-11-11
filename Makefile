# Makefile — Coherence Engine (Phase 2)

SHELL := /bin/bash
PY := $(shell command -v python3 || command -v python)
VENV := .venv
ACTIVATE := . $(VENV)/bin/activate;
APP_HOST := 0.0.0.0
APP_PORT := 8000
APP_MODULE := app.api:app
ENV_FILE := .env
ENV_EXAMPLE := .env.example
INCIDENTS_DIR := artifacts/incidents

# Persistence (defaults; override in .env if needed)
export PERSISTENCE ?= csv
export CSV_PATH ?= rolling_store.csv
export SQLITE_PATH ?= rolling_store.db

# Phase 2 runtime switch
export COHERENCE_MODE ?= demo   # demo | production

.PHONY: help venv install env api ui test fmt lint metrics metrics_new metrics_legacy \
        health status ingest automation-drift automation-demo incidents-dir \
        docker-build docker-run clean

help:
	@echo "Available targets:"
	@echo "  venv               - Create virtual environment"
	@echo "  install            - Install dependencies"
	@echo "  env                - Ensure .env exists and Phase-2 vars present"
	@echo "  api                - Run FastAPI backend"
	@echo "  ui                 - Run Streamlit dashboard"
	@echo "  metrics[_new|_legacy] - Query /coherence/metrics"
	@echo "  health | status    - Quick diagnostics"
	@echo "  automation-drift   - Emit a trust_continuity_alert (writes JSON)"
	@echo "  automation-demo    - Faster demo (1h window, low threshold)"
	@echo "  docker-build/run   - Build and run container"
	@echo "  test | fmt | lint  - QA tooling"
	@echo "  clean              - Remove venv and caches"

venv:
	@test -d $(VENV) || $(PY) -m venv $(VENV)
	@echo "✅ Virtual environment ready."

install: venv
	$(ACTIVATE) pip install --upgrade pip
	$(ACTIVATE) pip install -r requirements.txt
	@echo "✅ Dependencies installed."

env:
	@test -f $(ENV_FILE) || (test -f $(ENV_EXAMPLE) && cp $(ENV_EXAMPLE) $(ENV_FILE) || touch $(ENV_FILE); echo "Created $(ENV_FILE)")
	@grep -q '^COHERENCE_MODE=' $(ENV_FILE) || echo 'COHERENCE_MODE=$(COHERENCE_MODE)' >> $(ENV_FILE)
	@grep -q '^COHERENCE_WARN_THRESHOLD=' $(ENV_FILE) || echo 'COHERENCE_WARN_THRESHOLD=0.10' >> $(ENV_FILE)
	@grep -q '^COHERENCE_CRITICAL_THRESHOLD=' $(ENV_FILE) || echo 'COHERENCE_CRITICAL_THRESHOLD=0.25' >> $(ENV_FILE)
	@grep -q '^TREND_SENSITIVITY=' $(ENV_FILE) || echo 'TREND_SENSITIVITY=0.03' >> $(ENV_FILE)
	@grep -q '^STABILITY_HIGH_MIN=' $(ENV_FILE) || echo 'STABILITY_HIGH_MIN=0.80' >> $(ENV_FILE)
	@grep -q '^STABILITY_MEDIUM_MIN=' $(ENV_FILE) || echo 'STABILITY_MEDIUM_MIN=0.55' >> $(ENV_FILE)
	@grep -q '^UI_REFRESH_MS=' $(ENV_FILE) || echo 'UI_REFRESH_MS=3000' >> $(ENV_FILE)
	@grep -q '^API_BASE=' $(ENV_FILE) || echo 'API_BASE=http://localhost:8000' >> $(ENV_FILE)
	@echo "🔧 $(ENV_FILE) ready (COHERENCE_MODE=$${COHERENCE_MODE})"

api:
	$(ACTIVATE) uvicorn $(APP_MODULE) --host $(APP_HOST) --port $(APP_PORT) --reload

ui:
	$(ACTIVATE) streamlit run streamlit_app/app.py

test:
	$(ACTIVATE) pytest -q

fmt:
	-$(ACTIVATE) black app tests
	-$(ACTIVATE) isort app tests

lint:
	-$(ACTIVATE) flake8 app

# === Phase 2: semantic endpoints ===
metrics:
	curl -s "http://localhost:$(APP_PORT)/coherence/metrics" | $(PY) -m json.tool

metrics_new:
	curl -s "http://localhost:$(APP_PORT)/coherence/metrics?include_legacy=false" | $(PY) -m json.tool

metrics_legacy:
	curl -s "http://localhost:$(APP_PORT)/coherence/metrics?include_legacy=true" | $(PY) -m json.tool

# Utility endpoints
health:
	curl -s "http://localhost:$(APP_PORT)/health" | $(PY) -m json.tool

status:
	curl -s "http://localhost:$(APP_PORT)/status" | $(PY) -m json.tool

# Optional - only if you expose an ingest endpoint
ingest:
	curl -s "http://localhost:$(APP_PORT)/ingest/run" | $(PY) -m json.tool

# === Automation: write ledger-ready incidents ===
incidents-dir:
	mkdir -p $(INCIDENTS_DIR)

automation-drift: incidents-dir
	$(ACTIVATE) python -m automation.drift_sentry --window 24h --min-level medium

automation-demo: incidents-dir
	$(ACTIVATE) python -m automation.drift_sentry --window 1h --min-level low

# === Docker helpers ===
docker-build:
	docker build -t coherence-engine:latest .

docker-run:
	docker run --rm -p 8000:8000 --env-file $(ENV_FILE) -v "$$(pwd)/artifacts:/${INCIDENTS_DIR}" coherence-engine:latest

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache .mypy_cache .coverage **/*.pyc
	@echo "🧹 Clean complete."
