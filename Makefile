# Makefile for Applicant Validator
# Run `make help` to see available commands

.PHONY: help install install-prod test test-unit test-integration test-cov lint lint-fix format format-check fix typecheck check clean run dev \
        docker-up docker-down docker-logs docker-db-shell docker-reset db-migrate db-upgrade db-downgrade db-seed db-seed-flags db-seed-applicants \
        frontend-install frontend-dev frontend-build frontend-lint frontend-fix frontend-start

# Default target
.DEFAULT_GOAL := help

# Colors for terminal output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

#------------------------------------------------------------------------------
# Help
#------------------------------------------------------------------------------

help: ## Show this help message
	@echo "$(BLUE)Applicant Validator - Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Usage:$(NC) make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

#------------------------------------------------------------------------------
# Installation
#------------------------------------------------------------------------------

install: ## Install all dependencies (including dev tools)
	uv sync --extra dev

install-prod: ## Install production dependencies only
	uv sync

#------------------------------------------------------------------------------
# Testing
#------------------------------------------------------------------------------

test: ## Run all tests
	uv run pytest

test-unit: ## Run unit tests only
	uv run pytest tests/unit/ -v

test-integration: ## Run integration tests only (requires API credentials)
	uv run pytest tests/integration/ -v -m integration

test-cov: ## Run tests with coverage report
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html

test-cov-check: ## Run tests and fail if coverage is below threshold
	uv run pytest --cov=src --cov-fail-under=90

test-fast: ## Run tests without slow tests
	uv run pytest -m "not slow" -v

test-watch: ## Run tests in watch mode (requires pytest-watch)
	uv run pytest-watch -- -v

#------------------------------------------------------------------------------
# Code Quality
#------------------------------------------------------------------------------

lint: ## Run ruff linter
	uv run ruff check src tests

lint-fix: ## Run ruff linter with auto-fix
	uv run ruff check src tests --fix

format: ## Format code with ruff
	uv run ruff format src tests

format-check: ## Check code formatting without making changes
	uv run ruff format src tests --check

fix: ## Fix all linting and formatting issues
	uv run ruff check src tests --fix
	uv run ruff format src tests

typecheck: ## Run mypy type checker
	uv run mypy src

check: lint typecheck test ## Run all checks (lint, typecheck, test)

check-all: format-check lint typecheck test-cov-check ## Run all checks including format and coverage

#------------------------------------------------------------------------------
# Running the Application
#------------------------------------------------------------------------------

run: ## Run the API server
	uv run uvicorn applicant_validator.api.main:app --host 0.0.0.0 --port 8000

dev: ## Run the API server in development mode with auto-reload
	uv run uvicorn applicant_validator.api.main:app --reload --host 0.0.0.0 --port 8000

#------------------------------------------------------------------------------
# Cleanup
#------------------------------------------------------------------------------

clean: ## Remove build artifacts and cache files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true

clean-all: clean ## Remove all artifacts including virtual environment
	rm -rf .venv/

#------------------------------------------------------------------------------
# Development Utilities
#------------------------------------------------------------------------------

deps-update: ## Update all dependencies to latest versions
	uv lock --upgrade

deps-tree: ## Show dependency tree
	uv tree

pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install

pre-commit-run: ## Run pre-commit on all files
	uv run pre-commit run --all-files

#------------------------------------------------------------------------------
# Documentation
#------------------------------------------------------------------------------

docs-serve: ## Serve documentation locally (requires mkdocs)
	uv run mkdocs serve

docs-build: ## Build documentation
	uv run mkdocs build

#------------------------------------------------------------------------------
# Docker
#------------------------------------------------------------------------------

docker-up: ## Start PostgreSQL and services with Docker Compose
	docker compose up -d

docker-up-all: ## Start all services including pgAdmin
	docker compose --profile tools up -d

docker-down: ## Stop all Docker services
	docker compose --profile tools down

docker-logs: ## View Docker container logs
	docker compose logs -f

docker-db-shell: ## Open PostgreSQL shell
	docker compose exec postgres psql -U applicant_validator -d applicant_validator

docker-reset: ## Reset Docker volumes (WARNING: destroys data)
	docker compose --profile tools down -v
	docker compose up -d

docker-build: ## Rebuild Docker images
	docker compose build --no-cache

#------------------------------------------------------------------------------
# Database Migrations (Alembic) - Host
#------------------------------------------------------------------------------

db-migrate: ## Create a new migration (usage: make db-migrate msg="migration message")
	uv run alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## Apply all pending migrations
	uv run alembic upgrade head

db-downgrade: ## Rollback last migration
	uv run alembic downgrade -1

db-history: ## Show migration history
	uv run alembic history

db-current: ## Show current migration
	uv run alembic current

db-seed-flags: ## Seed flag types
	uv run python scripts/seed_flag_types.py

db-seed-applicants: ## Seed fake applicants (for testing)
	uv run python scripts/seed_applicants.py

db-seed: db-seed-flags ## Seed essential data (flags, etc.)

#------------------------------------------------------------------------------
# Frontend Commands
#------------------------------------------------------------------------------

FRONTEND_DIR := frontend

frontend-install: ## Install frontend dependencies
	cd $(FRONTEND_DIR) && npm install

frontend-dev: ## Run frontend dev server
	cd $(FRONTEND_DIR) && npm run dev

frontend-build: ## Build frontend for production
	cd $(FRONTEND_DIR) && npm run build

frontend-lint: ## Lint frontend code
	cd $(FRONTEND_DIR) && npm run lint

frontend-fix: ## Fix frontend linting issues
	cd $(FRONTEND_DIR) && npm run lint -- --fix

frontend-start: ## Start frontend production server
	cd $(FRONTEND_DIR) && npm run start

frontend-test: ## Run frontend tests
	cd $(FRONTEND_DIR) && npm test

frontend-test-watch: ## Run frontend tests in watch mode
	cd $(FRONTEND_DIR) && npm run test:watch

frontend-test-coverage: ## Run frontend tests with coverage
	cd $(FRONTEND_DIR) && npm run test:coverage
