# Makefile — Data Coherence Engine

SHELL := /bin/bash
PY := $(shell command -v python3 || command -v python)
VENV := .venv
ACTIVATE := . $(VENV)/bin/activate;
APP_HOST := 0.0.0.0
APP_PORT := 8000
ENV_EXAMPLE := .env.example
ENV_FILE := .env

export PERSISTENCE ?= csv
export CSV_PATH ?= rolling_store.csv
export SQLITE_PATH ?= rolling_store.db


.PHONY: install run test lint format clean streamlit env health status deps dev-freeze ingest

# -----------------------------------------------------------------------------
# Setup & Installation
# -----------------------------------------------------------------------------

install:
	$(PY) -m venv $(VENV)
	$(ACTIVATE) pip install -U pip
	$(ACTIVATE) pip install -r requirements.txt
	@test -f $(ENV_FILE) || (cp $(ENV_EXAMPLE) $(ENV_FILE) && echo "Created $(ENV_FILE) from $(ENV_EXAMPLE)")

deps:
	$(ACTIVATE) pip install -U pip
	$(ACTIVATE) pip install -r requirements.txt

dev-freeze:
	$(ACTIVATE) pip freeze > requirements-freeze.txt

# -----------------------------------------------------------------------------
# Run & Verification
# -----------------------------------------------------------------------------

run:
	$(ACTIVATE) uvicorn app.api:app --host $(APP_HOST) --port $(APP_PORT) --reload

streamlit:
	$(ACTIVATE) API_BASE="http://localhost:8000" streamlit run streamlit_app/app.py

automation-drift:
	$(ACTIVATE) python -m automation.drift_sentry --window 24h --fail-on-critical

# -----------------------------------------------------------------------------
# Testing & Quality
# -----------------------------------------------------------------------------

test:
	$(ACTIVATE) pytest -v

test-persistence:
	$(ACTIVATE) pytest -q tests/test_persistence.py tests/test_history_api.py

lint:
	$(ACTIVATE) black --check .
	$(ACTIVATE) pylint $$(git ls-files '*.py')

format:
	$(ACTIVATE) black .

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

env:
	@test -f $(ENV_FILE) || (cp $(ENV_EXAMPLE) $(ENV_FILE) && echo "Created $(ENV_FILE) from $(ENV_EXAMPLE)")

health:
	curl -s http://localhost:$(APP_PORT)/health | python -m json.tool

status:
	curl -s http://localhost:$(APP_PORT)/status | python -m json.tool

ingest:
	curl -s "http://localhost:$(APP_PORT)/ingest/run" | python -m json.tool

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache .mypy_cache .coverage *.pyc
