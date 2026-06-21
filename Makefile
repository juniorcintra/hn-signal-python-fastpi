.PHONY: help install test test-cov test-integration test-security lint format clean run migrate db-upgrade db-downgrade

help:
	@echo "Available commands:"
	@echo "  make install          - Install dependencies"
	@echo "  make test             - Run all tests"
	@echo "  make test-cov         - Run tests with coverage report"
	@echo "  make test-integration - Run only integration tests"
	@echo "  make test-security    - Run only security tests"
	@echo "  make lint             - Run linters (if configured)"
	@echo "  make format           - Format code (if configured)"
	@echo "  make clean            - Clean generated files"
	@echo "  make run              - Run development server"
	@echo "  make migrate          - Create new migration"
	@echo "  make db-upgrade       - Apply database migrations"
	@echo "  make db-downgrade     - Rollback last migration"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=app --cov-report=html --cov-report=term

test-integration:
	pytest tests/ -v -m integration

test-security:
	pytest tests/ -v -m security

test-fast:
	pytest tests/ -v -m "not slow"

lint:
	@echo "Linting not configured. Install ruff or flake8 if needed."

format:
	@echo "Formatting not configured. Install black or ruff if needed."

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

run:
	uvicorn app.main:app --reload

run-prod:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

migrate:
	alembic revision --autogenerate -m "$(msg)"

db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-reset:
	rm -f hn_articles.db
	alembic upgrade head

example:
	python examples/pipeline_client.py
