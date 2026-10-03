# Legal Lens backend. `make help` lists everything.
.DEFAULT_GOAL := help
.PHONY: help install dev run migrate migration seed reset test test-fast lint typecheck fmt check openapi clean

UV ?= uv

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies, including dev extras
	$(UV) sync --extra dev

dev: migrate ## Run the API with reload (http://127.0.0.1:8000)
	$(UV) run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

run: migrate ## Run the API without reload
	$(UV) run uvicorn app.main:app --host 0.0.0.0 --port 8000

migrate: ## Apply migrations
	$(UV) run alembic upgrade head

migration: ## Autogenerate a migration — make migration m="add x"
	@test -n "$(m)" || (echo 'usage: make migration m="what changed"' && exit 1)
	$(UV) run alembic revision --autogenerate -m "$(m)"

seed: migrate ## Create the dev user and the fixture corpus
	$(UV) run python -m app.seed

reset: ## Drop the database and blobs, then re-seed. Destructive.
	rm -f legallens.db legallens.db-wal legallens.db-shm
	rm -rf data/blobs data/work
	$(MAKE) seed

test: ## Run the test suite
	$(UV) run pytest

test-fast: ## Run the test suite, stopping at the first failure
	$(UV) run pytest -x -q

lint: ## Check formatting and lint rules
	$(UV) run ruff check app tests scripts
	$(UV) run ruff format --check app tests scripts

fmt: ## Apply formatting and safe lint fixes
	$(UV) run ruff check --fix app tests scripts
	$(UV) run ruff format app tests scripts

typecheck: ## Run mypy in strict mode
	$(UV) run mypy app

openapi: ## Regenerate openapi.json
	$(UV) run python scripts/export_openapi.py

check: lint typecheck ## Everything CI runs
	$(UV) run python scripts/export_openapi.py --check
	$(UV) run pytest -q

clean: ## Remove caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache
