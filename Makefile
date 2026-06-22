.PHONY: help install dev lint format test migrate migration db-push db-diff run docker-up docker-down seed clean frontend

SUPABASE := npx supabase

help:
	@echo "RAGForge - Production RAG System with RBAC"
	@echo ""
	@echo "Usage:"
	@echo "  make install          Install dependencies"
	@echo "  make dev              Run dev server with hot reload"
	@echo "  make lint             Run ruff linter"
	@echo "  make format           Run ruff formatter"
	@echo "  test                  Run tests"
	@echo "  make migration m=msg  Create a new SQL migration (writes to supabase/migrations/)"
	@echo "  make db-push          Apply pending migrations to remote Supabase"
	@echo "  make db-diff          Show diff between local and remote DB"
	@echo "  make db-status        Show migration status"
	@echo "  make run              Run production server"
	@echo "  make docker-up        Start all services"
	@echo "  make docker-down      Stop all services"
	@echo "  make seed             Seed roles and permissions"
	@echo "  make frontend         Run frontend dev server"
	@echo ""
	@echo "Prerequisites:"
	@echo "  - SUPABASE_ACCESS_TOKEN env var (get from https://supabase.com/dashboard/account/tokens)"
	@echo "  - Run 'supabase link --project-ref <ref>' to link this project"

install:
	uv sync --group app --group dev

dev:
	uv run --group app uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	uv run --group app --group dev ruff check app/

format:
	uv run --group app --group dev ruff format app/

test:
	uv run --group app --group dev pytest

migration:
	$(SUPABASE) migration new "$(m)"

db-push:
	$(SUPABASE) db push --linked

db-diff:
	$(SUPABASE) db diff --linked

db-status:
	$(SUPABASE) migration list

run:
	uv run --group app uvicorn app.main:app --host 0.0.0.0 --port 8000

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

seed:
	uv run python scripts/seed_roles.py

clean:
	rm -rf .venv
	rm -rf __pycache__ .pytest_cache
	rm -rf *.egg-info
