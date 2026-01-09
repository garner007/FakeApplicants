# Makefile for Applicant Validator
# Run `make help` to see available commands

.PHONY: help install install-dev test test-unit test-integration test-cov lint lint-fix format format-check fix typecheck check clean run dev \
        docker-up docker-down docker-logs docker-shell docker-db-shell docker-reset db-migrate db-upgrade db-downgrade db-seed db-seed-flags db-seed-applicants \
        dev-shell dev-fix-permissions dev-db-migrate dev-db-upgrade dev-db-downgrade dev-db-history dev-db-current dev-db-seed dev-db-seed-flags dev-db-seed-applicants dev-api dev-test dev-test-cov dev-lint dev-fix dev-typecheck dev-check \
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

install: ## Install production dependencies
	uv sync

install-dev: ## Install all dependencies including dev tools
	uv pip install -e ".[dev]"

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

docker-shell: ## Open shell in app container (dev container only)
	docker compose exec app bash

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

db-seed-applicants: ## Seed fake applicants
	uv run python scripts/seed_applicants.py

db-seed: db-seed-flags db-seed-applicants ## Seed all data (flags + applicants)

#------------------------------------------------------------------------------
# Dev Container Commands
#------------------------------------------------------------------------------

DEV_CONTAINER := applicant_validator_dev
DEV_EXEC := docker exec $(DEV_CONTAINER)
DEV_EXEC_IT := docker exec -it $(DEV_CONTAINER)
DEV_WORKDIR := /workspace

dev-shell: ## Open shell in dev container
	$(DEV_EXEC_IT) bash

dev-fix-permissions: ## Fix permissions in dev container (run if you get permission errors)
	$(DEV_EXEC) sudo chown -R vscode:vscode /home/vscode/.cache
	$(DEV_EXEC) sudo chown -R vscode:vscode /workspace/.venv 2>/dev/null || true

dev-db-migrate: ## Create a new migration in dev container (usage: make dev-db-migrate msg="message")
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run alembic revision --autogenerate -m '$(msg)'"

dev-db-upgrade: ## Apply all pending migrations in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run alembic upgrade head"

dev-db-downgrade: ## Rollback last migration in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run alembic downgrade -1"

dev-db-history: ## Show migration history in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run alembic history"

dev-db-current: ## Show current migration in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run alembic current"

dev-db-seed-flags: ## Seed flag types in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run python scripts/seed_flag_types.py"

dev-db-seed-applicants: ## Seed fake applicants in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run python scripts/seed_applicants.py"

dev-db-seed: dev-db-seed-flags dev-db-seed-applicants ## Seed all data in dev container

dev-api: ## Run API server in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run uvicorn applicant_validator.api.main:app --host 0.0.0.0 --port 8000 --reload"

dev-test: ## Run all tests in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run pytest"

dev-test-cov: ## Run tests with coverage in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run pytest --cov=src --cov-report=term-missing"

dev-lint: ## Run linter in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run ruff check src tests"

dev-fix: ## Fix all linting and formatting issues in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run ruff check src tests --fix && uv run ruff format src tests"

dev-typecheck: ## Run type checker in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run mypy src"

dev-check: ## Run all checks in dev container
	$(DEV_EXEC) bash -c "cd $(DEV_WORKDIR) && uv run ruff check src tests && uv run mypy src && uv run pytest"

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
