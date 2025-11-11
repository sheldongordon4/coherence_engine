# Makefile — Coherence Engine (Phase 2)

SHELL := /bin/bash
PY := $(shell command -v python3 || command -v python)
VENV := .venv
ACTIVATE := . $(VENV)/bin/activate;
APP_HOST := 0.0.0.0
APP_PORT := 8000
ENV_EXAMPLE := .env.example
ENV_FILE := .env

# Persistence (unchanged)
export PERSISTENCE ?= csv
export CSV_PATH ?= rolling_store.csv
export SQLITE_PATH ?= rolling_store.db

# Phase 2 runtime switch
export COHERENCE_MODE ?= demo   # demo | production

.PHONY: help venv install env dev api ui test fmt lint metrics metrics_new metrics_legacy health status ingest clean docker-build docker-run

help:
	@echo "Targets:"
	@echo "  venv            - create virtual env"
	@echo "  install         - install deps"
	@echo "  env             - ensure .env exists (adds COHERENCE_MODE if missing)"
	@echo "  dev / api       - run FastAPI locally (uvicorn)"
	@echo "  ui              - run Streamlit verification app"
	@echo "  test            - run pytest"
	@echo "  fmt             - format with black & isort (if present)"
	@echo "  lint            - lint with flake8 (if present)"
	@echo "  metrics         - GET /coherence/metrics (default window)"
	@echo "  metrics_new     - metrics with include_legacy=false"
	@echo "  metrics_legacy  - metrics with include_legacy=true"
	@echo "  health/status   - hit service health and status endpoints"
	@echo "  ingest          - trigger one-off ingest (if implemented)"
	@echo "  docker-build    - build container image"
	@echo "  docker-run      - run container (maps 8000)"
	@echo "  clean           - remove venv and caches"

venv:
	@test -d $(VENV) || $(PY) -m venv $(VENV)
	@echo "✅ venv ready: $(VENV)"

install: venv
	$(ACTIVATE) pip install --upgrade pip
	$(ACTIVATE) pip install -r requirements.txt
	@echo "✅ dependencies installed"

env:
	@test -f $(ENV_FILE) || (cp $(ENV_EXAMPLE) $(ENV_FILE) && echo "Created $(ENV_FILE) from $(ENV_EXAMPLE)")
	@grep -q '^COHERENCE_MODE=' $(ENV_FILE) || echo 'COHERENCE_MODE=$(COHERENCE_MODE)' >> $(ENV_FILE)
	@echo "🔧 $(ENV_FILE) ready (COHERENCE_MODE=$${COHERENCE_MODE})"

dev api:
	$(ACTIVATE) uvicorn app.api:app --host $(APP_HOST) --port $(APP_PORT) --reload

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

# Existing utilities (kept)
health:
	curl -s http://localhost:$(APP_PORT)/health | $(PY) -m json.tool

status:
	curl -s http://localhost:$(APP_PORT)/status | $(PY) -m json.tool

ingest:
	curl -s "http://localhost:$(APP_PORT)/ingest/run" | $(PY) -m json.tool

# Docker helpers (optional)
docker-build:
	docker build -t coherence-engine:latest .

docker-run:
	docker run --rm -p 8000:8000 --env-file $(ENV_FILE) coherence-engine:latest

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache .mypy_cache .coverage **/*.pyc
	@echo "🧹 cleaned"
