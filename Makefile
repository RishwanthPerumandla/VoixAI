.PHONY: install run test clean lint format help

VENV = venv
PYTHON = $(VENV)/Scripts/python
PIP = $(VENV)/Scripts/pip

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make run        - Run the application"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make lint       - Run linter"
	@echo "  make format     - Format code"

install:
	python -m venv $(VENV)
	$(PIP) install torch==2.4.0+cpu --index-url https://download.pytorch.org/whl/cpu
	$(PIP) install -r requirements.txt

dev-install: install
	$(PIP) install -r requirements-dev.txt

run:
	$(PYTHON) main.py

test:
	$(PYTHON) -m pytest tests/ -v

test-groq:
	$(PYTHON) test_groq.py

lint:
	$(PYTHON) -m flake8 core/ main.py
	$(PYTHON) -m pylint core/ main.py

format:
	$(PYTHON) -m black core/ main.py

clean:
	rm -rf __pycache__
	rm -rf core/__pycache__
	rm -rf .pytest_cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

db-clean:
	rm -f orders.db

backup-db:
	sqlite3 orders.db ".backup 'orders-backup-$(shell date +%Y%m%d-%H%M%S).db'"

health-check:
	curl http://localhost:8000/health
