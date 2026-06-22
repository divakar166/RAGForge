# RAGForge — Agent Guide

## Project Overview
Production-grade RAG system with multi-tenant org model for resume showcase. Dense+sparse vectors in Qdrant Cloud, TEI embeddings, httpx-based LLM client (OpenAI-compatible), Celery workers, Supabase (PostgreSQL), Langfuse tracing, RAGAS evaluation.

## Tech Stack
- **Runtime**: Python 3.12+, FastAPI, Uvicorn
- **Package manager**: UV (not pip/poetry)
- **Database**: Supabase (PostgreSQL via supabase-py REST client)
- **Vector store**: Qdrant Cloud (dense + sparse vectors, native RRF, payload filtering)
- **Cache/Queue**: Redis (Celery broker + rate limiter)
- **Async tasks**: Celery (sync SQLAlchemy engine for worker)
- **Embeddings**: Qdrant Cloud inference API at `/embed` (or TEI)
- **Sparse vectors**: rank_bm25 → Qdrant SparseVector
- **LLM**: httpx to any OpenAI-compatible API (OpenAI, vLLM, Ollama, Modal, NVIDIA)
- **Tracing**: Langfuse (`@observe` decorator on pipeline methods)
- **Evaluation**: RAGAS (faithfulness, answer_relevancy, context_precision, context_recall)
- **Auth**: JWT access + refresh tokens, bcrypt (direct, not passlib)
- **RBAC**: Org-level role-based access control (owner/admin/member) with Qdrant payload pre-filter

## Project Structure
```
RAGForge/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app, lifespan, CORS, health
│   ├── core/
│   │   ├── config.py               # Pydantic Settings (env-based)
│   │   ├── deps.py                 # DI: get_current_user, org context dependencies
│   │   ├── logger.py               # Logging config
│   │   └── security.py             # JWT create/verify, bcrypt hash/verify
│   ├── db/
│   │   ├── supabase.py             # Supabase client factory
│   │   └── schema.sql              # Full reference schema (source of truth)
│   ├── schemas/
│   │   ├── auth.py                 # Register/Login/Token schemas
│   │   ├── user.py                 # User CRUD schemas
│   │   ├── role.py                 # Role/Permission schemas
│   │   ├── document.py             # Document CRUD + access schemas
│   │   ├── search.py               # Search/RAG/Feedback schemas
│   │   ├── collection.py           # Collection schemas
│   │   ├── conversation.py         # Conversation thread schemas
│   │   ├── invitation.py           # Invitation schemas
│   │   └── organization.py         # Organization schemas
│   ├── api/v1/
│   │   ├── router.py               # Aggregates all endpoint routers
│   │   └── endpoints/
│   │       ├── auth.py             # /auth/register, /login, /refresh, /me
│   │       ├── users.py            # /users CRUD + role assignment
│   │       ├── roles.py            # /roles CRUD + permissions list
│   │       ├── invites.py          # /invites (verify/accept)
│   │       ├── evaluate.py         # /evaluate/run, /dataset
│   │       └── orgs/
│   │           ├── documents.py    # /orgs/{id}/documents CRUD + access + download
│   │           ├── search.py       # /orgs/{id}/search/query, /ask, /history, /feedback
│   │           ├── collections.py  # /orgs/{id}/collections CRUD
│   │           ├── conversations.py# /orgs/{id}/conversations + threads
│   │           ├── members.py      # /orgs/{id}/members CRUD
│   │           ├── invites.py      # /orgs/{id}/invites CRUD
│   │           ├── audit.py        # /orgs/{id}/audit log
│   │           └── evaluate.py     # /orgs/{id}/evaluate
│   ├── services/
│   │   ├── auth.py                 # register, authenticate, login, refresh
│   │   ├── rbac.py                 # has_permission, assign_roles, etc.
│   │   ├── audit.py                # log_action
│   │   ├── orgs.py                 # Org creation, member management
│   │   └── rate_limit.py           # Redis sliding-window rate limiter
│   ├── rag/
│   │   ├── chunking/
│   │   │   ├── __init__.py         # Chunk dataclass, ChunkingStrategy ABC
│   │   │   ├── recursive.py        # Structure-aware recursive chunking
│   │   │   ├── semantic.py         # Embedding-similarity breakpoints
│   │   │   └── pipeline.py         # Strategy selection by file type
│   │   ├── embeddings.py           # TEIEmbeddingProvider, OpenAIEmbeddingProvider
│   │   ├── sparse.py               # BM25SparseEncoder
│   │   ├── vector_store.py         # QdrantStore (upsert, hybrid_search, RBAC filter)
│   │   ├── retrieval.py            # RetrievalPipeline (search with @observe)
│   │   ├── reranker.py             # TEI /rerank + local CrossEncoder fallback
│   │   ├── llm.py                  # LLMClient (httpx, OpenAI-compatible, @observe)
│   │   ├── generation.py           # build_context, generate_answer (@observe)
│   │   └── parser.py               # parse_document (pdf, docx, txt, md, html)
│   ├── evaluation/
│   │   └── __init__.py             # RAGAS metrics, golden dataset, CI gate
│   ├── monitoring/
│   │   └── tracing.py              # Langfuse init, @observe, score_trace
│   └── workers/
│       └── tasks.py                # Celery process_document task
├── supabase/
│   └── migrations/
│       ├── 20260616000000_initial_schema.sql
│       └── 20260616000001_add_conversation_threads.sql
├── scripts/
│   ├── seed_roles.py               # Seed admin/editor/viewer roles
│   ├── ci_eval.py                  # RAGAS CI gate
│   └── demo_bootstrap.py           # Full demo setup (legacy, uses SQLAlchemy)
├── data/
│   └── golden_dataset.json         # RAGAS evaluation dataset
├── frontend/
│   ├── app/
│   │   ├── (auth)/login/page.tsx
│   │   ├── (auth)/register/page.tsx
│   │   ├── dashboard/
│   │   │   ├── page.tsx            # Dashboard home
│   │   │   ├── layout.tsx          # Sidebar + org context
│   │   │   ├── chat/page.tsx       # Chat UI with threads
│   │   │   ├── search/page.tsx     # Search interface
│   │   │   ├── history/page.tsx    # Conversation history
│   │   │   ├── documents/page.tsx  # Document list
│   │   │   ├── documents/[id]/page.tsx  # Document detail + preview
│   │   │   ├── collections/page.tsx     # Collection list
│   │   │   ├── collections/[id]/page.tsx # Collection detail
│   │   │   └── admin/
│   │   │       ├── users/page.tsx
│   │   │       ├── roles/page.tsx
│   │   │       ├── members/page.tsx
│   │   │       ├── invites/page.tsx
│   │   │       ├── audit/page.tsx
│   │   │       └── evaluate/page.tsx
│   │   ├── invite/page.tsx         # Invite acceptance
│   │   └── page.tsx                # Landing page
│   ├── lib/
│   │   ├── api.ts                  # API client (all endpoints)
│   │   ├── types.ts                # TypeScript interfaces
│   │   ├── auth-context.tsx         # Auth provider + hooks
│   │   ├── theme-context.tsx        # Theme provider
│   │   ├── format.ts               # Date formatting utilities
│   │   └── utils.ts                # cn() helper
│   └── components/
│       └── ui/                     # shadcn/ui components
├── tests/
│   ├── test_rag/
│   │   └── test_chunking.py        # 3 tests: recursive, headings, empty
│   └── test_rbac/
│       ├── test_permissions.py     # 5 tests: admin, specific, lacks, any, list
│       └── test_security.py        # 3 tests: hashing, token, invalid
├── docker-compose.yml              # Services: app, worker, postgres, redis, qdrant, tei
├── Dockerfile                      # App image
├── Dockerfile.worker               # Worker image
├── Makefile                        # Common commands
├── pyproject.toml                  # UV/package config
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
- Celery worker uses **sync** SQLAlchemy engine for direct DB ops (psycopg2, not asyncpg)
- `ensure_collection` in QdrantStore is **sync** — called from both lifespan and Celery worker
- bcrypt used directly (not passlib) due to bcrypt 5.0+ API breakage
- Default member role auto-assigned on registration
- Document access control stored in Qdrant point payload (`allowed_role_ids`, `allowed_user_ids`, `is_public`, `owner_id`)
- `RERANKER_MODEL` is not in settings by default — `hasattr` check in reranker.py
- Langfuse is opt-in (disabled by default); enable via `LANGFUSE_ENABLED=true` + set keys (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`)
- Langfuse is initialized eagerly in app lifespan and flushed on shutdown
- The `/search/ask` endpoint wraps the full RAG pipeline in a unified trace with `user_id` + `session_id` propagated via `propagate_attributes`

### Dependency Groups
Deps are split into groups for lean Docker images:
- `[project].dependencies` — shared (httpx, qdrant-client, rank-bm25, numpy, sqlalchemy, pydantic-settings, bcrypt, python-multipart, supabase)
- `--group app` — app-only (fastapi, uvicorn, python-jose, redis, langfuse, ragas, datasets, pandas, langchain-openai)
- `--group worker` — worker-only (celery, psycopg2-binary, pdfplumber, python-docx)
- `--group dev` — dev tools (pytest, ruff, mypy, aiosqlite)
- Dev setup: `uv sync --group app --group dev`
- App Docker: `uv sync --no-dev --group app`
- Worker Docker: `uv sync --no-dev --group worker`
- `app/workers/celery_app.py` is a lean module (only `celery` import) so the app can dispatch tasks via `send_task()` without importing the worker's heavy task deps.

### RAG Pipeline Flow
1. User uploads document → Celery `process_document` task
2. Task: parse → chunk (recursive/semantic) → embed dense (Qdrant Cloud inference) + sparse (BM25) → upsert to Qdrant
3. User searches: embed query → hybrid search with RBAC filter → rerank (TEI) → format results
4. User asks: same search + LLM generation with citations
5. All pipeline steps traced via Langfuse `@observe` if enabled

### Multi-Tenant Org Model
- On registration, user creates an organization (becomes owner)
- Org members have roles: `owner`, `admin`, `member`
- All data is scoped to `organization_id` in both Supabase and Qdrant payload
- Endpoints are prefixed with `/api/v1/orgs/{org_id}/`
- Invitation system for adding members (email + token)
- Audit log tracks all actions per org

### Database Migrations (Supabase CLI)
- Migrations live in `supabase/migrations/` as timestamped `.sql` files
- Create: `make migration m="description"` (runs `supabase migration new`)
- Apply: `make db-push` (runs `supabase db push --linked`)
- Prerequisite: `SUPABASE_ACCESS_TOKEN` env var + `supabase link --project-ref <ref>` first run
- Do NOT use Alembic — Supabase CLI handles migration ordering, rollbacks, and remote sync
- For local dev, use local Supabase: `supabase start`

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
