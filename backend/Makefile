.PHONY: help install install-dev test test-cov lint format format-check type-check ci docker-build docker-up docker-down clean

help:
	@echo "MOS Backend - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install production dependencies"
	@echo "  make install-dev      Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format           Format code with Black"
	@echo "  make format-check     Check code formatting (no changes)"
	@echo "  make lint             Run Flake8 linter"
	@echo "  make type-check       Run MyPy type checker"
	@echo "  make ci               Run all CI checks (format, lint, type, test)"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run tests"
	@echo "  make test-cov         Run tests with coverage report"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     Build Docker images"
	@echo "  make docker-up        Start Docker services"
	@echo "  make docker-down      Stop Docker services"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove cache and build files"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	flake8 app/ tests/ --max-line-length=100 --extend-ignore=E203,W503

format:
	black app/ tests/

format-check:
	black --check --diff app/ tests/

type-check:
	mypy app/ --ignore-missing-imports --no-strict-optional

ci: format-check lint type-check test
	@echo ""
	@echo "✓ All CI checks passed!"

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo ""
	@echo "Waiting for services to be ready..."
	@sleep 5
	@docker-compose ps

docker-down:
	docker-compose down

docker-down-volumes:
	docker-compose down -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage coverage.xml
	@echo "Cleaned up cache and build files"
