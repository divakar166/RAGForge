.PHONY: help install dev lint format test migrate run docker-up docker-down clean

help:
	@echo "RAGForge - Production RAG System with RBAC"
	@echo ""
	@echo "Usage:"
	@echo "  make install       Install dependencies"
	@echo "  make dev           Run dev server with hot reload"
	@echo "  make lint          Run ruff linter"
	@echo "  make format        Run ruff formatter"
	@echo "  test               Run tests"
	@echo "  make migrate       Run database migrations"
	@echo "  make revision m=msg  Create new migration"
	@echo "  make run           Run production server"
	@echo "  make docker-up     Start all services"
	@echo "  make docker-down   Stop all services"
	@echo "  make seed          Seed roles and permissions"

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

migrate:
	uv run --group app alembic upgrade head

revision:
	uv run --group app alembic revision --autogenerate -m "$(m)"

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
