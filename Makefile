# Makefile — Data Coherence Engine

SHELL := /bin/bash
VENV  := .venv
ACTIVATE := . $(VENV)/bin/activate;

.PHONY: install run test lint format clean streamlit

install:
	python3.11 -m venv $(VENV)
	$(ACTIVATE) pip install -U pip
	$(ACTIVATE) pip install -r requirements.txt

run:
	$(ACTIVATE) uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload

test:
	$(ACTIVATE) pytest -v

lint:
	$(ACTIVATE) pylint $$(git ls-files '*.py')
	$(ACTIVATE) black --check .

format:
	$(ACTIVATE) black .

streamlit:
	$(ACTIVATE) API_BASE="http://localhost:8000" streamlit run streamlit_app.py

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache .mypy_cache .ruff_cache
