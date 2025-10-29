# Makefile for Data Coherence Engine v0.1

PYTHON=python
VENV=.venv
ACTIVATE=. $(VENV)/bin/activate;

help:
	@echo "Available commands:"
	@echo "  make install     - Create venv and install dependencies"
	@echo "  make run         - Run the FastAPI server locally"
	@echo "  make test        - Run pytest suite"
	@echo "  make lint        - Run lint and formatting checks (non-destructive)"
	@echo "  make format      - Auto-format with Black and Ruff (destructive)"
	@echo "  make streamlit   - Launch Streamlit verification app"
	@echo "  make clean       - Remove build artifacts"

install:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) pip install -r requirements.txt

run:
	$(ACTIVATE) uvicorn app:app --reload --port 8000

test:
	$(ACTIVATE) pytest -v

lint:
	$(ACTIVATE) ruff check .
	$(ACTIVATE) black --check .

format:
	$(ACTIVATE) black .
	$(ACTIVATE) ruff check . --fix

streamlit:
	$(ACTIVATE) API_BASE="http://localhost:8000" streamlit run streamlit_app.py

clean:
	rm -rf __pycache__ .pytest_cache *.pyc *.pyo *.pyd *.db *.csv
	rm -rf $(VENV)
