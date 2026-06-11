# RAGForge — Agent Guide

## Project Overview
Production-grade RAG system with RBAC for resume showcase. Dense+sparse vectors in Qdrant, TEI embeddings, httpx-based LLM client (OpenAI-compatible), Celery workers, PostgreSQL, Langfuse tracing, RAGAS evaluation.

## Tech Stack
- **Runtime**: Python 3.12+, FastAPI, Uvicorn
- **Package manager**: UV (not pip/poetry)
- **Database**: PostgreSQL (async via asyncpg + SQLAlchemy 2.0)
- **Vector store**: Qdrant (dense + sparse vectors, native RRF, payload filtering)
- **Cache/Queue**: Redis (Celery broker + rate limiter)
- **Async tasks**: Celery (sync SQLAlchemy engine for worker)
- **Embeddings**: TEI (Text Embeddings Inference) at `/embed` and `/rerank`
- **Sparse vectors**: rank_bm25 → Qdrant SparseVector
- **LLM**: httpx to any OpenAI-compatible API (OpenAI, vLLM, Ollama, Modal)
- **Tracing**: Langfuse (`@observe` decorator on pipeline methods)
- **Evaluation**: RAGAS (faithfulness, answer_relevancy, context_precision, context_recall)
- **Auth**: JWT access + refresh tokens, bcrypt (direct, not passlib)
- **RBAC**: Role/Permission model with defense-in-depth (Qdrant pre-filter + service-layer post-filter + audit log)

## Project Structure
```
RAGForge/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan, CORS, health
│   ├── core/
│   │   ├── config.py              # Pydantic Settings (env-based)
│   │   ├── deps.py                # DI: get_current_user, get_current_admin
│   │   ├── logger.py              # Logging config
│   │   └── security.py            # JWT create/verify, bcrypt hash/verify
│   ├── db/
│   │   ├── session.py             # Async engine + session factory
│   │   ├── base.py                # Declarative base
│   │   └── models/
│   │       ├── user.py            # User model
│   │       ├── role.py            # Role model + user_roles table
│   │       ├── permission.py      # Permission + role_permissions table
│   │       ├── document.py        # Document model
│   │       ├── audit_log.py       # AuditLog model
│   │       └── mixins.py          # UUIDPKMixin, TimestampMixin
│   ├── schemas/
│   │   ├── auth.py                # Register/Login/Token schemas
│   │   ├── user.py                # User CRUD schemas
│   │   ├── role.py                # Role/Permission schemas
│   │   ├── document.py            # Document schemas
│   │   └── search.py              # Search/RAG/Feedback schemas
│   ├── api/v1/
│   │   ├── router.py              # Aggregates all endpoint routers
│   │   └── endpoints/
│   │       ├── auth.py            # /auth/register, /login, /refresh, /me
│   │       ├── users.py           # /users CRUD + role assignment
│   │       ├── roles.py           # /roles CRUD + permissions list
│   │       ├── documents.py       # /documents upload/list/get/delete/access
│   │       ├── search.py          # /search/query, /ask, /history, /feedback
│   │       └── evaluate.py        # /evaluate/run, /dataset
│   ├── services/
│   │   ├── auth.py                # register, authenticate, login, refresh
│   │   ├── rbac.py                # has_permission, assign_roles, etc.
│   │   ├── audit.py               # log_action
│   │   └── rate_limit.py          # Redis sliding-window rate limiter
│   ├── rag/
│   │   ├── chunking/
│   │   │   ├── __init__.py        # Chunk dataclass, ChunkingStrategy ABC
│   │   │   ├── recursive.py       # Structure-aware recursive chunking
│   │   │   ├── semantic.py        # Embedding-similarity breakpoints
│   │   │   └── pipeline.py        # Strategy selection by file type
│   │   ├── embeddings.py          # TEIEmbeddingProvider, OpenAIEmbeddingProvider
│   │   ├── sparse.py              # BM25SparseEncoder
│   │   ├── vector_store.py        # QdrantStore (upsert, hybrid_search, RBAC filter)
│   │   ├── retrieval.py           # RetrievalPipeline (search with @observe)
│   │   ├── reranker.py            # TEI /rerank + local CrossEncoder fallback
│   │   ├── llm.py                 # LLMClient (httpx, OpenAI-compatible, @observe)
│   │   ├── generation.py          # build_context, generate_answer (@observe)
│   │   └── parser.py              # parse_document (pdf, docx, txt, md, html)
│   ├── evaluation/
│   │   └── __init__.py            # RAGAS metrics, golden dataset, CI gate
│   ├── monitoring/
│   │   └── tracing.py             # Langfuse init, @observe, score_trace
│   └── workers/
│       └── tasks.py               # Celery process_document task
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 7def11ec86d5_initial.py  # Full initial migration (7 tables)
├── scripts/
│   ├── seed_roles.py              # Seed admin/editor/viewer + 9 permissions
│   └── ci_eval.py                 # RAGAS CI gate
├── data/
│   └── golden_dataset.json        # RAGAS evaluation dataset
├── frontend/
│   └── README.md                  # API ref, stack, build plan
├── tests/
│   ├── test_rag/
│   │   └── test_chunking.py       # 3 tests: recursive, headings, empty
│   └── test_rbac/
│       ├── test_permissions.py    # 5 tests: admin, specific, lacks, any, list
│       └── test_security.py       # 3 tests: hashing, token, invalid
├── docker-compose.yml             # 6 services: app, worker, postgres, redis, qdrant, tei
├── Dockerfile                     # App image
├── Dockerfile.worker              # Worker image
├── Makefile                       # Common commands
├── pyproject.toml                 # UV/package config
└── .env.example
```

## Key Conventions

### Code Style
- No comments in code unless absolutely necessary
- Type hints everywhere
- Pydantic v2 for schemas
- FastAPI dependency injection pattern
- Async endpoints, sync Celery workers

### Critical Config Details
- `ALLOWED_EXTENSIONS` is comma-separated **string** (not list) — split on use to avoid pydantic-settings JSON decode error
- Celery worker uses **sync** SQLAlchemy engine (`DATABASE_URL` with psycopg2, not asyncpg)
- `ensure_collection` in QdrantStore is **sync** — called from both lifespan and Celery worker
- bcrypt used directly (not passlib) due to bcrypt 5.0+ API breakage
- Default viewer role auto-assigned on registration; admin/editor manually assigned via API
- Document access control stored in Qdrant point payload (`allowed_role_ids`, `allowed_user_ids`, `is_public`, `owner_id`)
- `RERANKER_MODEL` is not in settings by default — `hasattr` check in reranker.py
- Langfuse is opt-in (disabled by default); enable via `LANGFUSE_ENABLED=true` + set keys (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`)
- Langfuse is initialized eagerly in app lifespan and flushed on shutdown
- The `/search/ask` endpoint wraps the full RAG pipeline in a unified trace with `user_id` + `session_id` propagated via `propagate_attributes`

### Dependency Groups
Deps are split into groups for lean Docker images:
- `[project].dependencies` — shared (httpx, qdrant-client, rank-bm25, numpy, sqlalchemy, pydantic-settings, bcrypt, python-multipart)
- `--group app` — app-only (fastapi, uvicorn, asyncpg, python-jose, redis, langfuse, ragas, datasets, pandas, langchain-openai, alembic)
- `--group worker` — worker-only (celery, psycopg2-binary, pdfplumber, python-docx)
- `--group dev` — dev tools (pytest, ruff, mypy, aiosqlite)
- Dev setup: `uv sync --group app --group dev`
- App Docker: `uv sync --no-dev --group app`
- Worker Docker: `uv sync --no-dev --group worker`
- `app/workers/celery_app.py` is a lean module (only `celery` import) so the app can dispatch tasks via `send_task()` without importing the worker's heavy task deps.

### RAG Pipeline Flow
1. User uploads document → Celery `process_document` task
2. Task: parse → chunk (recursive/semantic) → embed dense (TEI) + sparse (BM25) → upsert to Qdrant
3. User searches: embed query → hybrid search with RBAC filter → rerank (TEI) → format results
4. User asks: same search + LLM generation with citations
5. All pipeline steps traced via Langfuse `@observe` if enabled

### RBAC Model
- **Pre-filter**: Qdrant payload filter (`is_public`, `owner_id`, `allowed_role_ids`)
- **Post-filter**: Service layer `has_permission` / `has_any_permission`
- **Audit**: Every action logged to `audit_logs` table
- **Permissions**: `document:create`, `document:read`, `document:update`, `document:delete`, `search:query`, `users:manage`, `roles:manage`, `evaluate:run`, `admin:full`
- **Roles**: admin (all), editor (document CRUD + search), viewer (read + search)

### Testing
- Framework: pytest with pytest-asyncio
- Run: `uv run pytest` or `make test`
- 11 tests currently (chunking: 3, RBAC: 5, security: 3)
- No test containers yet (no DB/Qdrant mocking)

### Evaluation CI Gate
- RAGAS metrics: faithfulness ≥ 0.80, answer_relevancy ≥ 0.75, context_precision ≥ 0.70, context_recall ≥ 0.70
- Run: `uv run python scripts/ci_eval.py`
- Golden dataset: `data/golden_dataset.json`

### Docker Services
| Service | Port | Purpose |
|---------|------|---------|
| app | 8000 | FastAPI app |
| worker | — | Celery async tasks |
| frontend | 3000 | Next.js app |
| postgres | 5432 | Relational DB |
| redis | 6379 | Cache + broker |
| qdrant | 6333 | Vector store |
| tei | 8080 | TEI inference |

All images run as non-root user. Frontend uses Next.js `output: standalone` for minimal size.
Docker Compose services use `restart: unless-stopped` and healthchecks for production readiness.
