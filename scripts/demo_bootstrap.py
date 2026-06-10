#!/usr/bin/env python
"""Demo bootstrap — creates users, roles, synthetic documents, and runs ingestion.

Usage:
    uv run python scripts/demo_bootstrap.py

Requirements:
    - PostgreSQL, Qdrant, Redis, TEI must be running (via docker-compose)
    - Alembic migration must have been run (or this script runs it)

What it does:
    1. Runs Alembic migrations (creates all tables)
    2. Seeds roles (admin/editor/viewer) + permissions
    3. Creates demo users (admin, editor, viewer)
    4. Generates synthetic resume/job description documents as .md files
    5. Parses → chunks → embeds (TEI) → sparse vectors (BM25) → upserts to Qdrant
    6. Prints summary with login credentials
"""
import asyncio
import logging
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("demo_bootstrap")

# ──────────────────────────── Demo Documents ────────────────────────────

DEMO_DOCUMENTS = [
    {
        "title": "Senior Software Engineer — Resume",
        "file_name": "senior-engineer-resume.md",
        "content": """# Jane Doe

## Senior Software Engineer

Email: jane.doe@example.com | Phone: +1 (555) 123-4567

## Summary

Senior Software Engineer with 8+ years of experience building distributed systems, microservices, and ML pipelines. Proficient in Python, Go, and Rust. Passionate about system design, developer tooling, and open source.

## Experience

### Senior Backend Engineer — DataCorp (2020–Present)
- Architected a real-time data pipeline processing 50k events/sec using Kafka, Flink, and Redis
- Reduced P99 latency by 60% by migrating from monolithic to event-driven microservices
- Led a team of 5 engineers; introduced code review standards and CI/CD best practices
- Built an internal developer platform serving 200+ engineers across 15 teams

### Software Engineer — CloudStack (2017–2020)
- Designed and implemented multi-tenant RBAC system for SaaS platform (10k+ organizations)
- Developed GraphQL API serving 1M+ daily requests with <100ms P99 latency
- Containerized legacy monolith into 12 microservices deployed on Kubernetes
- Wrote comprehensive integration tests achieving 95% code coverage

### Junior Developer — StartupXYZ (2015–2017)
- Built RESTful APIs with FastAPI and PostgreSQL for B2B analytics platform
- Implemented OAuth2/OIDC authentication flow used by 50+ enterprise customers
- Automated infrastructure provisioning with Terraform and Ansible

## Education

### M.Sc. Computer Science — Stanford University (2013–2015)
- Thesis: "Efficient Distributed Consensus in Unreliable Networks"
- GPA: 3.9/4.0

### B.Sc. Computer Science — UC Berkeley (2009–2013)
- Dean's List, ACM Programming Contest finalist

## Skills

**Languages:** Python, Go, Rust, TypeScript, SQL
**Frameworks:** FastAPI, Django, React, Spring Boot
**Infrastructure:** Kubernetes, Docker, Terraform, AWS, GCP
**Data:** PostgreSQL, Redis, Kafka, Flink, Qdrant, Elasticsearch
**ML/AI:** PyTorch, scikit-learn, LangChain, RAG pipelines, embeddings

## Open Source Contributions
- Core contributor to FastAPI framework (37 merged PRs)
- Author of `pyrate-limiter` — Redis-based rate limiting library (2k+ GitHub stars)
- Maintainer of `qdrant-py` — community Python SDK examples
""",
    },
    {
        "title": "ML Engineering Lead — Job Description",
        "file_name": "ml-lead-jd.md",
        "content": """# Machine Learning Engineering Lead

**Location:** San Francisco, CA (Hybrid)
**Department:** AI/ML Platform
**Reports to:** VP of Engineering

## About Us

DataCorp is building the next-generation data intelligence platform. We process petabytes of data daily and serve insights to Fortune 500 companies. Our AI/ML team develops production-grade models and infrastructure that power real-time recommendations, anomaly detection, and predictive analytics.

## Role

We're looking for an ML Engineering Lead to own our ML inference platform serving 1M+ predictions/second. You'll lead a team of 6 ML engineers and work closely with data scientists, infrastructure engineers, and product teams.

## Responsibilities

- Design and operate the ML inference platform serving 1M+ predictions/second across 50+ models
- Lead a team of 6 ML engineers through technical design, code review, and mentorship
- Build and maintain feature stores, model registries, and A/B testing infrastructure
- Optimize model serving latency (target P99 <50ms) using GPU acceleration and model quantization
- Collaborate with data scientists to productionize research models (NLP, computer vision, recommendation)
- Establish monitoring, alerting, and incident response for ML systems
- Drive ML platform roadmap and contribute to quarterly OKR planning

## Requirements

### Must-Have
- 7+ years of software engineering experience, 3+ in ML infrastructure
- Strong programming skills in Python and at least one systems language (Go, Rust, C++)
- Deep understanding of production ML systems: feature engineering, model serving, monitoring
- Experience with container orchestration (Kubernetes, Docker) and cloud platforms (AWS/GCP)
- Track record of leading engineering teams and mentoring junior engineers

### Nice-to-Have
- Experience with vector databases (Qdrant, Pinecone, Weaviate) and RAG architectures
- Contributions to open source ML projects
- Experience with LLM fine-tuning and deployment (vLLM, TGI, TensorRT-LLM)
- Knowledge of MLOps tools (MLflow, Kubeflow, Weights & Biases)

## Tech Stack

**Core:** Python, Go, PyTorch, TensorFlow, scikit-learn
**Infrastructure:** Kubernetes, Docker, Terraform, AWS SageMaker
**Data:** PostgreSQL, Redis, Kafka, Qdrant, Parquet
**ML Serving:** vLLM, TGI, Triton Inference Server, ONNX Runtime
**Observability:** Prometheus, Grafana, Langfuse, OpenTelemetry

## Benefits

- Competitive salary ($200k–$280k) + equity package
- 401(k) with 6% company match
- Unlimited PTO (min 3 weeks encouraged)
- Annual learning budget ($5k)
- Remote-friendly with SF office
""",
    },
    {
        "title": "Distributed Systems — Technical Blog Post",
        "file_name": "distributed-systems-blog.md",
        "content": """# Building Resilient Distributed Systems: A Practical Guide

## Introduction

Distributed systems are the backbone of modern applications. Whether you're building a microservices architecture, a data pipeline, or a real-time analytics platform, understanding distributed system principles is critical for building reliable software at scale.

## Key Concepts

### 1. Consensus Algorithms

Consensus algorithms like Raft and Paxos allow distributed systems to agree on state despite failures. Raft, designed for understandability, uses a leader-based approach:

- **Leader Election:** Nodes vote for a leader; the candidate with majority votes becomes leader
- **Log Replication:** Leader appends entries to its log and replicates to followers
- **Safety:** At most one leader per term; committed entries are never lost

Practical implementation considerations:
- Use etcd or Consul for production consensus (don't build your own Raft)
- Configure proper timeouts to avoid frequent leader elections
- Monitor cluster health with leadership change alerts

### 2. Event-Driven Architecture

Event-driven systems decouple producers from consumers using message brokers:

**Pattern: Event Sourcing**
Instead of storing current state, store all state-changing events. This provides:
- Complete audit trail of all changes
- Ability to rebuild state from events
- Temporal queries (state at any point in time)

**Pattern: CQRS (Command Query Responsibility Segregation)**
Separate write models (commands) from read models (queries):
- Commands go to the write database (normalized, ACID)
- Queries come from read replicas (denormalized, optimized for queries)
- Events synchronize write side to read side

### 3. Distributed Tracing

Observability in distributed systems requires tracing requests across service boundaries:

- **Trace Context:** Propagate trace_id and span_id via HTTP headers (W3C Trace Context)
- **Span Attributes:** Record service name, operation, duration, status code
- **Sampling:** Head-based (consistent) or tail-based (selective) sampling

Tools: OpenTelemetry, Jaeger, Zipkin, Langfuse

## Real-World Patterns

### Circuit Breaker

Prevent cascading failures by detecting when a downstream service is unhealthy:

```
CLOSED → (failures exceed threshold) → OPEN → (timeout elapses) → HALF_OPEN
  ↑                                                                │
  └────────────────── (success) ←──────────────────────────────────┘
```

### Bulkhead

Isolate resources to prevent failure in one part from taking down the whole system. Common implementations:
- Thread pool isolation (separate pools for different services)
- Connection pool isolation (separate DB connection pools per service)
- Queue isolation (separate queues per tenant or workload)

### Rate Limiting with Token Bucket

A classic algorithm for controlling request rates:
- Tokens are added to a bucket at a fixed rate (e.g., 100 tokens/second)
- Each request consumes one token
- Requests without tokens are throttled (429 Too Many Requests)

## Conclusion

Building resilient distributed systems requires thoughtful architecture, careful implementation, and comprehensive observability. Start with simple patterns (retries, timeouts) and layer on more complex patterns (circuit breakers, bulkheads) as your system grows.
""",
    },
    {
        "title": "RAG Systems — Architecture Guide",
        "file_name": "rag-architecture-guide.md",
        "content": """# Retrieval-Augmented Generation: Architecture Guide

## What is RAG?

Retrieval-Augmented Generation (RAG) combines a retrieval system with a generative LLM to produce grounded, factual responses. Instead of relying solely on the LLM's parametric knowledge, RAG retrieves relevant documents from a knowledge base and conditions the LLM on that context.

## Core Components

### 1. Ingestion Pipeline

```
Document → Parser → Chunker → Embedder → Vector Store
                              └→ Sparse Encoder ┘
```

- **Parser:** Extract text from PDFs, DOCX, HTML, Markdown
- **Chunker:** Split text into manageable pieces (recursive, semantic, or hybrid)
- **Embedder:** Generate dense vector representations (TEI, OpenAI, BGE)
- **Sparse Encoder:** Generate sparse vectors (BM25) for lexical matching
- **Vector Store:** Store and index vectors for fast retrieval (Qdrant, Pinecone)

### 2. Query Pipeline

```
Query → Embed Query → Hybrid Search → Reranker → LLM → Answer
         └→ Sparse Query ┘     ↑
                          RBAC Filter
```

- **Hybrid Search:** Combines dense (semantic) and sparse (keyword) retrieval
- **Fusion:** Reciprocal Rank Fusion (RRF) merges results from multiple strategies
- **Reranker:** Cross-encoder model re-ranks top results for precision
- **Generation:** LLM generates context-grounded answer with citations

### 3. Evaluation Pipeline

Assess RAG quality with RAGAS metrics:
- **Faithfulness:** Are all claims in the answer grounded in the context?
- **Answer Relevancy:** Does the answer address the question?
- **Context Precision:** Is the retrieved context relevant?
- **Context Recall:** Does the context contain all needed information?

## Best Practices

### Chunking Strategy

| Document Type | Recommended Strategy | Chunk Size |
|--------------|---------------------|------------|
| Code/markdown | Recursive (heading-aware) | 256–512 tokens |
| Narrative text | Semantic (embedding-based) | 384–768 tokens |
| Legal/technical | Recursive (section-aware) | 512–1024 tokens |

### Embedding Selection

- **all-MiniLM-L6-v2** (384d): Fast, good for general purpose
- **BAAI/bge-base-en-v1.5** (768d): Better quality, good for retrieval
- **text-embedding-3-large** (3072d): Best quality, slower, OpenAI-only

### Vector Store Configuration

- Use COSINE distance for normalized embeddings
- Enable payload indexing for metadata filtering (RBAC, dates, categories)
- Configure proper quantization (Scalar Quantization reduces memory 4x)
- Set up collection aliases for zero-downtime reindexing

## Production Considerations

- **RBAC:** Filter results by user/role permissions at query time
- **Caching:** Cache frequent queries and embeddings
- **Monitoring:** Trace every pipeline step with Langfuse/OpenTelemetry
- **Evaluation:** Run RAGAS CI gate before deploying model changes
- **A/B Testing:** Compare retrieval strategies on quality metrics + latency
""",
    },
    {
        "title": "Langfuse — LLM Observability Platform Overview",
        "file_name": "langfuse-overview.md",
        "content": """# Langfuse: Open Source LLM Observability

## Overview

Langfuse is an open source observability platform for LLM applications. It provides tracing, monitoring, and evaluation for production AI systems. Think of it as Datadog for LLMs.

## Key Features

### 1. Tracing

Every LLM call, retrieval step, and generation is captured as part of a trace tree:

```
Trace (user query)
├── Span: Retrieval (hybrid search)
│   ├── Span: Embedding generation
│   └── Span: Qdrant search
├── Span: Reranking
└── Span: LLM Generation
    ├── Input: system prompt + context + question
    └── Output: generated answer + token usage
```

### 2. Evaluation Scores

Attach quality scores to traces for monitoring:
- **Automated:** RAGAS metrics (faithfulness, relevancy)
- **Human:** User feedback (thumbs up/down)
- **LLM-as-Judge:** Automated scoring using a judge model

### 3. Prompt Management

Version, test, and deploy prompts from the Langfuse UI:
- Track prompt changes over time
- A/B test different prompt versions
- Roll back to previous versions instantly

### 4. Cost & Latency Monitoring

Track token usage, cost, and latency across models:
- Per-model cost breakdown
- P50/P95/P99 latency distributions
- Token usage trends over time

## Integration

### Python SDK

```python
from langfuse.decorators import observe

@observe(name="rag_pipeline")
def handle_query(query: str):
    # This becomes the root trace
    results = retrieve(query)  # Child span
    answer = generate(query, results)  # Child span
    return answer
```

### Scoring

```python
from langfuse import Langfuse
lf = Langfuse()

# Human feedback
lf.score(
    trace_id="abc123",
    name="user_satisfaction",
    value=1,  # thumbs up
    data_type="BOOLEAN",
)

# Automated metric
lf.score(
    trace_id="abc123",
    name="faithfulness",
    value=0.92,
    data_type="NUMERIC",
)
```

## Configuration

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

## Self-Hosting

Langfuse can be self-hosted via Docker Compose:
- PostgreSQL for trace storage
- S3/MinIO for large payloads
- Background workers for async processing

## Use Cases

1. **Debugging:** Find exactly which retrieval step failed or returned bad results
2. **Quality Monitoring:** Track faithfulness scores over time; get alerts on regressions
3. **Cost Optimization:** Identify expensive model calls and optimize prompt lengths
4. **A/B Testing:** Compare retrieval strategies end-to-end with quality metrics
5. **Compliance:** Audit trail of all LLM interactions with full trace visibility
""",
    },
    {
        "title": "System Design Interview — URL Shortener",
        "file_name": "system-design-url-shortener.md",
        "content": """# System Design: URL Shortener

## Requirements

### Functional
- Generate a short, unique alias for a long URL
- Redirect short URL to original URL (302 redirect)
- Optional: custom aliases, expiration, analytics

### Non-Functional
- High availability (99.99% uptime)
- Low latency (<10ms redirect)
- Scalable to billions of URLs
- Durable — never lose a mapping

## High-Level Design

```
Client → Load Balancer → Web Servers → Cache (Redis)
                                        └→ Database (PostgreSQL)
                                              └→ Backup (S3)
```

## Key Design Decisions

### 1. Key Generation

**Approach: Base62 Encoding of Auto-Increment ID**

Generate unique IDs using a distributed ID service (Snowflake or Redis INCR):
- Snowflake: 41-bit timestamp + 10-bit worker + 12-bit sequence = 64-bit ID
- Base62 encode: 62^7 = 3.5 trillion combinations → 7 characters

**Approach: Pre-generate Keys**

Generate keys in batches and store them in a key pool:
- Reduces write contention
- Allows for key reuse (recycling expired keys)
- Simplifies redirect path (no write on redirect)

### 2. Database Schema

```sql
CREATE TABLE urls (
    id BIGSERIAL PRIMARY KEY,
    short_key VARCHAR(10) UNIQUE NOT NULL,
    original_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    user_id VARCHAR(36),
    click_count BIGINT DEFAULT 0
);

CREATE INDEX idx_short_key ON urls(short_key);
```

### 3. Caching Strategy

**Cache-Aside Pattern:**

1. On redirect, check Redis first (TTL: 24 hours)
2. On cache miss, query PostgreSQL
3. Populate cache with the result
4. Return redirect

For popular URLs, consider write-through cache to avoid thundering herd.

### 4. Analytics Pipeline

Track clicks with async event processing:
- Web servers emit click events to Kafka
- Flink consumes and aggregates into Redis counters
- Periodic snapshots written to PostgreSQL
- Dashboard queries Redis for real-time stats

## Scale Estimates

| Metric | Value |
|--------|-------|
| Daily writes | 100M new URLs |
| Daily reads | 10B redirects |
| Storage | 100M × 500 bytes = 50 GB/day |
| Bandwidth | 10B × 1KB = 10 TB/day |

## Advanced Features

### Custom Aliases
- Add a custom_alias column with unique constraint
- Allow users to specify their own short key
- Validate custom alias availability before assignment

### Expiration
- TTL-based expiration (auto-delete after N days)
- Soft-delete with cleanup job
- Recycle expired keys back to the pool

### Rate Limiting
- Token bucket per user/IP
- 1000 URLs/hour for free tier
- 100k URLs/hour for paid tier

## Monitoring

- Redirect latency (P50 <5ms, P99 <20ms)
- Cache hit rate (>99%)
- Key pool utilization
- Error rate (4xx, 5xx)
- Write throughput (URLs/second)
""",
    },
    {
        "title": "Python Async Best Practices",
        "file_name": "python-async-guide.md",
        "content": """# Python Async Best Practices

## When to Use Async

Async is great for I/O-bound workloads:
- HTTP requests (API calls, web scraping)
- Database queries (PostgreSQL, Redis, MongoDB)
- File I/O (disk reads/writes)
- Network communication (WebSockets, gRPC)

Async is NOT helpful for CPU-bound workloads:
- Complex computations
- Image/video processing
- ML model inference (use separate threads/processes)

## Core Patterns

### 1. Proper Session Management

```python
# GOOD: Use context managers
async with httpx.AsyncClient() as client:
    resp = await client.get("https://api.example.com/data")
    return resp.json()

# BAD: Creating clients per request without reuse
async def fetch(url):
    client = httpx.AsyncClient()
    resp = await client.get(url)
    await client.aclose()  # Easy to forget
    return resp.json()
```

### 2. Concurrent Execution

```python
import asyncio

# Run tasks concurrently with gather
async def fetch_all(urls):
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
    return [r.json() for r in responses if not isinstance(r, Exception)]
```

### 3. Timeouts Are Critical

```python
import asyncio

async def fetch_with_timeout(url):
    try:
        async with asyncio.timeout(5):
            async with httpx.AsyncClient() as client:
                return await client.get(url)
    except asyncio.TimeoutError:
        logger.warning("Request to %s timed out", url)
        return None
```

### 4. Rate Limiting

```python
import asyncio

class RateLimiter:
    def __init__(self, rate: int, per: float = 1.0):
        self.rate = rate
        self.per = per
        self._tokens = rate
        self._last_refill = asyncio.get_event_loop().time()

    async def acquire(self):
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_refill
        self._tokens = min(self.rate, self._tokens + elapsed * self.rate / self.per)
        self._last_refill = now
        if self._tokens < 1:
            wait = (1 - self._tokens) * self.per / self.rate
            await asyncio.sleep(wait)
            self._tokens = 0
        else:
            self._tokens -= 1
```

## FastAPI-Specific Patterns

### Dependency Injection

```python
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

@app.get("/items/{item_id}")
async def get_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    return item
```

### Background Tasks

```python
from fastapi import BackgroundTasks

@app.post("/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    doc_id = await save_document(...)
    background_tasks.add_task(process_document, doc_id)
    return {"document_id": doc_id, "status": "processing"}
```

## Common Pitfalls

1. **Mixing sync and async:** Avoid blocking the event loop with sync calls (use `run_in_executor`)
2. **Forgotten awaits:** Always `await` coroutines, or use `asyncio.ensure_future` for fire-and-forget
3. **Shared mutable state:** Use `asyncio.Lock` for shared resource access
4. **Connection pool exhaustion:** Always close sessions/clients
5. **Exception handling:** Use `return_exceptions=True` with `gather` to avoid losing results
""",
    },
]

# ────────────────────────── Bootstrap Logic ─────────────────────────────


async def run_migrations():
    """Run Alembic migrations to head."""
    logger.info("Running Alembic migrations...")
    from alembic.config import Config as AlembicConfig
    from alembic import command

    alembic_cfg = AlembicConfig("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations complete.")


async def seed_roles_and_permissions(db):
    """Seed roles (admin, editor, viewer) and all permissions."""
    from app.db.models.permission import Permission
    from app.db.models.role import Role

    existing = await db.execute(Role.__table__.select().limit(1))
    if existing.fetchone():
        logger.info("Roles already seeded, skipping.")
        return

    DEFAULT_PERMISSIONS = [
        {"codename": "document:create", "name": "Create Documents", "resource_type": "document", "action": "create"},
        {"codename": "document:read", "name": "Read Documents", "resource_type": "document", "action": "read"},
        {"codename": "document:update", "name": "Update Documents", "resource_type": "document", "action": "update"},
        {"codename": "document:delete", "name": "Delete Documents", "resource_type": "document", "action": "delete"},
        {"codename": "search:query", "name": "Search Documents", "resource_type": "search", "action": "query"},
        {"codename": "users:manage", "name": "Manage Users", "resource_type": "users", "action": "manage"},
        {"codename": "roles:manage", "name": "Manage Roles", "resource_type": "roles", "action": "manage"},
        {"codename": "admin:full", "name": "Full Admin Access", "resource_type": "admin", "action": "*"},
        {"codename": "evaluate:run", "name": "Run Evaluations", "resource_type": "evaluate", "action": "run"},
    ]

    perm_map = {}
    for p_def in DEFAULT_PERMISSIONS:
        perm = Permission(**p_def)
        db.add(perm)
        await db.flush()
        perm_map[p_def["codename"]] = perm

    ROLES_CONFIG = {
        "admin": {
            "description": "Full system access",
            "is_system_role": True,
            "permissions": ["*"],
        },
        "editor": {
            "description": "Can upload and manage documents",
            "is_system_role": True,
            "permissions": ["document:create", "document:read", "document:update", "document:delete", "search:query"],
        },
        "viewer": {
            "description": "Can search and read documents",
            "is_system_role": True,
            "permissions": ["document:read", "search:query"],
        },
    }

    roles_map = {}
    for role_name, role_def in ROLES_CONFIG.items():
        role = Role(name=role_name, description=role_def["description"], is_system_role=role_def["is_system_role"])
        db.add(role)
        await db.flush()
        if role_def["permissions"] == ["*"]:
            role.permissions = list(perm_map.values())
        else:
            role.permissions = [perm_map[pc] for pc in role_def["permissions"] if pc in perm_map]
        roles_map[role_name] = role

    await db.commit()
    logger.info("Seeded 9 permissions and 3 roles (admin, editor, viewer).")
    return roles_map


async def create_demo_users(db, roles_map):
    """Create demo users: admin, editor, viewer."""
    from app.db.models.user import User
    from app.core.security import hash_password

    DEMO_USERS = [
        {"username": "admin", "email": "admin@ragforge.dev", "password": "admin123", "role": "admin"},
        {"username": "editor", "email": "editor@ragforge.dev", "password": "editor123", "role": "editor"},
        {"username": "viewer", "email": "viewer@ragforge.dev", "password": "viewer123", "role": "viewer"},
    ]

    created = []
    for u_def in DEMO_USERS:
        existing = await db.execute(User.__table__.select().where(User.username == u_def["username"]))
        if existing.fetchone():
            logger.info("User '%s' already exists, skipping.", u_def["username"])
            continue

        user = User(
            username=u_def["username"],
            email=u_def["email"],
            hashed_password=hash_password(u_def["password"]),
            is_active=True,
            is_superuser=(u_def["role"] == "admin"),
        )
        db.add(user)
        await db.flush()

        role = roles_map.get(u_def["role"])
        if role:
            user.roles = [role]

        created.append({**u_def, "id": str(user.id)})

    await db.commit()
    if created:
        logger.info("Created %d demo users.", len(created))
    return created


async def ingest_demo_documents(db, upload_dir: str):
    """Generate synthetic documents, ingest via RAG pipeline (sync)."""
    from app.db.models.document import Document
    from app.rag.chunking.pipeline import ChunkingPipeline
    from app.rag.parser import parse_document
    from app.rag.sparse import BM25SparseEncoder
    from app.rag.vector_store import QdrantStore
    from qdrant_client import models as qmodels
    import httpx

    os.makedirs(upload_dir, exist_ok=True)

    # Get admin user as owner
    from app.db.models.user import User
    result = await db.execute(User.__table__.select().where(User.username == "admin"))
    admin_row = result.fetchone()
    if not admin_row:
        logger.error("Admin user not found; cannot ingest documents.")
        return []
    admin_id = str(admin_row[0])
    logger.info("Using admin user (id=%s) as document owner.", admin_id)

    store = QdrantStore()
    ingested = []

    for doc_def in DEMO_DOCUMENTS:
        file_path = os.path.join(upload_dir, doc_def["file_name"])
        with open(file_path, "w") as f:
            f.write(doc_def["content"])

        existing = await db.execute(
            Document.__table__.select().where(Document.title == doc_def["title"])
        )
        if existing.fetchone():
            logger.info("Document '%s' already exists in DB, skipping ingestion.", doc_def["title"])
            continue

        doc = Document(
            title=doc_def["title"],
            file_path=file_path,
            file_type="md",
            file_size=len(doc_def["content"]),
            status="processing",
            owner_id=admin_id,
            is_public=True,
        )
        db.add(doc)
        await db.flush()
        doc_id = str(doc.id)
        logger.info("Created document record: %s (%s)", doc_def["title"], doc_id)

        # Parse
        text = parse_document(file_path)
        if not text.strip():
            doc.status = "failed"
            await db.commit()
            logger.warning("Empty content for %s, skipping.", doc_def["title"])
            continue

        # Chunk
        pipeline = ChunkingPipeline()
        chunks = pipeline.chunk(text, doc_def["title"], "md", "recursive")
        logger.info("  Chunked into %d chunks", len(chunks))

        # Embed via TEI (sync httpx)
        chunk_texts = [c.content for c in chunks]
        batch_size = 32
        all_embeddings = []
        tei_endpoint = os.environ.get("TEI_ENDPOINT", "http://localhost:8080").rstrip("/")

        with httpx.Client(timeout=120) as client:
            for i in range(0, len(chunk_texts), batch_size):
                batch = chunk_texts[i : i + batch_size]
                resp = client.post(f"{tei_endpoint}/embed", json={"inputs": batch})
                resp.raise_for_status()
                data = resp.json()
                embeddings = data if isinstance(data, list) else data.get("data", [])
                all_embeddings.extend(embeddings)
        logger.info("  Generated %d dense embeddings", len(all_embeddings))

        # Sparse vectors
        sparse_encoder = BM25SparseEncoder()
        sparse_encoder.fit(chunk_texts)
        all_sparse = [sparse_encoder.encode(t) for t in chunk_texts]

        # Build Qdrant points
        points = []
        for j, chunk in enumerate(chunks):
            sparse_indices, sparse_values = all_sparse[j]
            point = qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "dense": all_embeddings[j] if j < len(all_embeddings) else [],
                    "sparse": qmodels.SparseVector(indices=sparse_indices, values=sparse_values),
                },
                payload={
                    "document_id": doc_id,
                    "chunk_index": chunk.index,
                    "doc_title": doc_def["title"],
                    "section_path": chunk.section_path or "",
                    "strategy": chunk.strategy,
                    "content": chunk.content,
                    "owner_id": admin_id,
                    "is_public": True,
                    "allowed_role_ids": [],
                    "allowed_user_ids": [],
                },
            )
            points.append(point)

        # Upsert to Qdrant
        vector_size = len(all_embeddings[0]) if all_embeddings else 384
        store.ensure_collection(vector_size)
        store.upsert_chunks(points)

        doc.status = "indexed"
        await db.commit()
        ingested.append({"id": doc_id, "title": doc_def["title"], "chunks": len(points)})
        logger.info("  Indexed %d points to Qdrant.", len(points))

    return ingested


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="RAGForge demo bootstrap")
    parser.add_argument("--upload-dir", default="./uploads/demo", help="Directory for demo files")
    parser.add_argument("--skip-migrations", action="store_true", help="Skip Alembic migrations")
    args = parser.parse_args()

    upload_dir = os.path.abspath(args.upload_dir)

    print("""
╔══════════════════════════════════════════════╗
║        RAGForge Demo Bootstrap               ║
╚══════════════════════════════════════════════╝
""")

    # 1. Migrations
    if not args.skip_migrations:
        await run_migrations()
    else:
        logger.info("Skipping migrations (--skip-migrations).")

    # 2. DB setup
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        # 3. Seed roles
        roles_map = await seed_roles_and_permissions(db)

        # 4. Create demo users
        users = await create_demo_users(db, roles_map)

        # 5. Ingest demo documents
        ingested = await ingest_demo_documents(db, upload_dir)

    await engine.dispose()

    # ── Summary ──
    print("""
╔══════════════════════════════════════════════╗
║        Bootstrap Complete!                   ║
╚══════════════════════════════════════════════╝
""")
    print("Demo Users:")
    print(f"  {'Username':<12} {'Password':<14} {'Role':<10} {'Email'}")
    print(f"  {'-'*12} {'-'*14} {'-'*10} {'-'*30}")
    all_users = users if users else [
        {"username": "admin", "password": "admin123", "email": "admin@ragforge.dev", "role": "admin"},
        {"username": "editor", "password": "editor123", "email": "editor@ragforge.dev", "role": "editor"},
        {"username": "viewer", "password": "viewer123", "email": "viewer@ragforge.dev", "role": "viewer"},
    ]
    for u in all_users:
        print(f"  {u['username']:<12} {u['password']:<14} {u['role']:<10} {u['email']}")

    print(f"\nIngested Documents: {len(ingested)}")
    for d in ingested:
        print(f"  - {d['title']} ({d['chunks']} chunks)")

    print(f"\nUpload directory: {upload_dir}")
    print(f"\nAPI: http://localhost:8000/api/v1")
    print(f"Docs: http://localhost:8000/docs")
    print("""
Quick test:
  curl -X POST http://localhost:8000/api/v1/auth/login \\
    -H "Content-Type: application/json" \\
    -d '{"username": "admin", "password": "admin123"}'

  curl -X POST http://localhost:8000/api/v1/search/query \\
    -H "Content-Type: application/json" \\
    -H "Authorization: Bearer <token>" \\
    -d '{"query": "What is RAG?", "top_k": 3}'
""")


if __name__ == "__main__":
    asyncio.run(main())
