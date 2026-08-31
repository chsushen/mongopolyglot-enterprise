.PHONY: help install seed test run lint clean docker-up docker-down

PYTHON ?= python3
PIP ?= pip
UVICORN ?= uvicorn
PYTEST ?= pytest

help:
	@echo "MongoPolyglot Enterprise - Development & Operational Commands"
	@echo "=============================================================="
	@echo "  make install     Install required dependencies from requirements.txt"
	@echo "  make seed        Seed standard McDonald's NYC and E-Commerce datasets"
	@echo "  make test        Run complete pytest suite with execution timing"
	@echo "  make run         Launch FastAPI & Mission Control Dashboard on port 8000"
	@echo "  make lint        Check syntax and code formatting"
	@echo "  make clean       Remove cached bytecode, coverage, and temp database files"
	@echo "  make docker-up   Build and launch containerized services via docker-compose"
	@echo "  make docker-down Terminate and remove docker-compose containers"

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

seed:
	PYTHONPATH=. $(PYTHON) scripts/seed_mcdonalds_dataset.py
	PYTHONPATH=. $(PYTHON) scripts/seed_ecommerce_dataset.py

test:
	PYTHONPATH=. $(PYTEST) tests/ -v

run:
	PYTHONPATH=. $(UVICORN) backend.app.main:app --host 0.0.0.0 --port 8000 --reload

lint:
	PYTHONPATH=. $(PYTHON) -m py_compile backend/app/main.py scripts/seed_mcdonalds_dataset.py scripts/seed_ecommerce_dataset.py
	@echo "✅ Code syntax validation passed."

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	rm -f polyglot_relational.db
	@echo "✅ Workspace cleaned."

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down
