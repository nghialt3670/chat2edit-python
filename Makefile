.PHONY: help install lint format format-check type-check syntax-check import-check import-fix check build clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	poetry install

lint: ## Run linting checks (ruff)
	poetry run ruff check src/

format-check: ## Check code formatting (black)
	poetry run black --check src/

format: ## Format code (black)
	poetry run black src/

import-check: ## Check imports (unused, missing, sorting, errors)
	@echo "=== Checking for unused imports (F401) ==="
	poetry run ruff check --select F401 src/
	@echo "=== Checking for undefined names/imports (F821) ==="
	poetry run ruff check --select F821 src/
	@echo "=== Checking for redefined imports (F811) ==="
	poetry run ruff check --select F811 src/
	@echo "=== Checking import sorting (I) ==="
	poetry run ruff check --select I src/

import-fix: ## Auto-fix import sorting
	poetry run ruff check --select I --fix src/

type-check: ## Run type checking (mypy)
	poetry run mypy src/

syntax-check: ## Check Python syntax
	find src -name "*.py" -exec poetry run python -m py_compile {} \;

check: lint import-check format-check type-check syntax-check ## Run all checks

build: check ## Build package after running all checks
	poetry build

clean: ## Clean build artifacts
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

