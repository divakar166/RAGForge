# RAGForge

Production-grade, multi-tenant RAG system with RBAC, built for document intelligence.

## Architecture

```
User → FastAPI → Supabase (auth, metadata, audit)
             → Qdrant Cloud (dense + sparse vectors)
             → Celery worker (async document processing)
             → LLM API (OpenAI-compatible)
```

## Quick Start

### Prerequisites
- Python 3.12+, Node.js 18+, UV
- Supabase project (cloud or local)
- Qdrant Cloud cluster
- Redis
- LLM API key (OpenAI, NVIDIA, vLLM, etc.)

### Setup

```bash
# Clone and install
git clone <repo> && cd RAGForge
cp .env.example .env
# Edit .env with your Supabase URL, service key, Qdrant creds, LLM key
uv sync --group app --group dev

# Run migrations
npx supabase link --project-ref <your-project-ref>
make db-push

# Start
make dev                    # FastAPI on :8000
cd frontend && npm install && npm run dev  # Next.js on :3000

# In another terminal (for document processing):
uv run --group worker celery -A app.workers.celery_app worker --loglevel=info
```

## Project Map

| Layer | Tech | Purpose |
|-------|------|---------|
| **API** | FastAPI + Uvicorn | REST endpoints, org-scoped |
| **Database** | Supabase (Postgres) | Users, orgs, documents metadata, conversations, audit |
| **Vector Store** | Qdrant Cloud | Hybrid search (dense + sparse), RBAC payload filters |
| **Queue** | Redis + Celery | Document parsing, chunking, indexing |
| **Embedding** | Qdrant Cloud Inference API | Dense vectors (all-MiniLM-L6-v2) |
| **LLM** | httpx → OpenAI-compatible API | Answer generation with citations |
| **Frontend** | Next.js 16 (App Router) | Dashboard, chat, admin panels |
| **Auth** | JWT (access + refresh) | bcrypt hashing, org-scoped |
| **Tracing** | Langfuse (opt-in) | Full RAG pipeline traces |

## Key Design Decisions

- **Org-scoped everything**: All data isolated by `organization_id` in both Supabase and Qdrant payloads
- **Supabase CLI migrations**: No Alembic — raw SQL migrations managed via `supabase migration new` + `db push`
- **Document access control**: Qdrant payload pre-filter (`allowed_role_ids`, `is_public`) — not DB-level filtering
- **Dependency groups**: `app`, `worker`, `dev` — lean Docker images, workers don't import app deps

## API

Full reference in [`API.md`](./API.md). Key endpoints:

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/register` | Register user + create org |
| `POST /api/v1/auth/login` | Login |
| `POST /api/v1/orgs/{id}/documents/upload` | Upload document |
| `POST /api/v1/orgs/{id}/search/query` | Hybrid search |
| `POST /api/v1/orgs/{id}/search/ask` | RAG query with LLM answer |
| `GET /api/v1/orgs/{id}/collections` | List collections |
| `GET /api/v1/orgs/{id}/conversations` | List conversation threads |
| `POST /api/v1/orgs/{id}/members` | Invite member |

## Development

```bash
make lint          # ruff check
make format        # ruff format
make test          # pytest
make migration m="msg"  # new Supabase migration
make db-push       # apply migrations
```

## License

Private — internal use.
