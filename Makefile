.PHONY: install dev test test-unit test-integration lint format docker-up docker-down clean help frontend-install frontend-dev frontend-build

# Default target
help:
	@echo "Luma Labs API - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install backend dependencies"
	@echo "  make frontend-install Install frontend dependencies"
	@echo "  make docker-up        Start Redis and Playwright in Docker"
	@echo "  make docker-down      Stop Docker services"
	@echo ""
	@echo "Development:"
	@echo "  make dev              Run API with hot reload (port 8000)"
	@echo "  make frontend-dev     Run frontend dev server (port 5173)"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-int         Run integration tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linter (ruff + mypy)"
	@echo "  make format           Format code with ruff"
	@echo ""
	@echo "Build:"
	@echo "  make frontend-build   Build frontend for production"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove build artifacts"

# Install dependencies
install:
	pip install -e ".[dev]"

# Run development server
dev:
	uvicorn luma_api.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
test:
	pytest -v --cov=luma_api --cov-report=term-missing

# Run unit tests only
test-unit:
	pytest tests/unit -v

# Run integration tests only
test-int:
	pytest tests/integration -v

# Run linter
lint:
	ruff check src tests
	mypy src

# Format code
format:
	ruff format src tests
	ruff check --fix src tests

# Start Docker services
docker-up:
	docker-compose up -d redis playwright

# Stop Docker services
docker-down:
	docker-compose down

# Full Docker environment
docker-all:
	docker-compose up --build

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Frontend commands
frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

# Quick start: install deps, start Redis, run API
run: install docker-up
	@echo "Waiting for Redis to start..."
	@sleep 2
	$(MAKE) dev

# Full stack: install all, start Redis, run both servers
full-stack: install frontend-install docker-up
	@echo "Starting full stack (run 'make dev' and 'make frontend-dev' in separate terminals)"
	@echo ""
	@echo "Terminal 1: make dev          (API on http://localhost:8000)"
	@echo "Terminal 2: make frontend-dev (Frontend on http://localhost:5173)"
