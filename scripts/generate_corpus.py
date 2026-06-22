"""
Enterprise Knowledge Base Corpus Generator
============================================
Generates 30 realistic PDF documents across Engineering, Product, and Confidential
departments for testing a production-grade RAG system with RBAC.

Intentional overlaps:
  - Project Atlas:     engineering, product, confidential
  - Project Phoenix:   engineering, product, confidential
  - Qdrant:            engineering, product
  - March 2026 incident: engineering, confidential

Intentional conflicts:
  - Feature X launch date: July vs August
  - Project Atlas budget:  $2.4M vs $2.8M
"""

import os
import csv
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

#  Output paths 
BASE_DIR      = "data"
ENG_DIR       = os.path.join(BASE_DIR, "engineering")
PROD_DIR      = os.path.join(BASE_DIR, "product")
CONF_DIR      = os.path.join(BASE_DIR, "confidential")
METADATA_PATH = os.path.join(BASE_DIR, "metadata.csv")

#  Style helpers 
def build_styles():
    """Return a dict of custom ReportLab paragraph styles."""
    base = getSampleStyleSheet()

    styles = {
        "doc_title": ParagraphStyle(
            "DocTitle",
            parent=base["Title"],
            fontSize=20,
            spaceAfter=6,
            textColor=colors.HexColor("#1a1a2e"),
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#666677"),
            spaceAfter=2,
        ),
        "classification_public": ParagraphStyle(
            "ClassPub",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#2d6a4f"),
            spaceAfter=8,
            fontName="Helvetica-Bold",
        ),
        "classification_internal": ParagraphStyle(
            "ClassInt",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#e76f51"),
            spaceAfter=8,
            fontName="Helvetica-Bold",
        ),
        "classification_confidential": ParagraphStyle(
            "ClassConf",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#c1121f"),
            spaceAfter=8,
            fontName="Helvetica-Bold",
        ),
        "exec_summary_box": ParagraphStyle(
            "ExecSummary",
            parent=base["Normal"],
            fontSize=10,
            leading=15,
            leftIndent=12,
            rightIndent=12,
            spaceAfter=12,
            textColor=colors.HexColor("#2b2d42"),
            backColor=colors.HexColor("#f0f4ff"),
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontSize=13,
            textColor=colors.HexColor("#1a1a2e"),
            spaceBefore=14,
            spaceAfter=4,
            borderPad=2,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontSize=11,
            textColor=colors.HexColor("#34344a"),
            spaceBefore=10,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=10,
            leading=15,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            leftIndent=18,
            spaceAfter=3,
            bulletIndent=6,
        ),
    }
    return styles


def build_table(headers, rows, col_widths=None):
    """Return a styled ReportLab Table flowable."""
    data = [headers] + rows
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  9),
        ("ALIGN",        (0, 0), (-1, -1), "LEFT"),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#f7f7fc"), colors.white]),
        ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#ccccdd")),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    return tbl


def write_pdf(filepath, metadata, sections):
    """
    Build and save a PDF document.

    Parameters
    ----------
    filepath : str
        Absolute output path.
    metadata : dict
        Keys: title, author, department, classification, date
    sections : list of dict
        Each dict has 'heading' (str) and 'content' (list of flowables or strings).
        A string is auto-wrapped in a Body Paragraph.
        Use {"table": (headers, rows, widths)} for tables.
        Use {"bullets": [...]} for bullet lists.
    """
    S = build_styles()

    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        title=metadata["title"],
        author=metadata["author"],
        subject=metadata["department"],
    )

    story = []

    #  Classification banner 
    cl_style = {
        "public":       S["classification_public"],
        "internal":     S["classification_internal"],
        "confidential": S["classification_confidential"],
    }.get(metadata["classification"], S["classification_internal"])
    story.append(Paragraph(f"[{metadata['classification'].upper()}]", cl_style))

    #  Title 
    story.append(Paragraph(metadata["title"], S["doc_title"]))
    story.append(HRFlowable(width="100%", thickness=1.5,
                             color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 6))

    #  Document meta block 
    for line in [
        f"<b>Author:</b> {metadata['author']}",
        f"<b>Department:</b> {metadata['department']}",
        f"<b>Last Updated:</b> {metadata['date']}",
        f"<b>Classification:</b> {metadata['classification']}",
    ]:
        story.append(Paragraph(line, S["meta"]))
    story.append(Spacer(1, 10))

    #  Sections 
    for sec in sections:
        heading = sec.get("heading")
        if heading:
            lvl = sec.get("level", 1)
            story.append(Paragraph(heading, S["h1"] if lvl == 1 else S["h2"]))

        for item in sec.get("content", []):
            if isinstance(item, str):
                story.append(Paragraph(item, S["body"]))
            elif isinstance(item, dict):
                if "table" in item:
                    hdrs, rows, widths = item["table"]
                    story.append(Spacer(1, 4))
                    story.append(build_table(hdrs, rows, widths))
                    story.append(Spacer(1, 8))
                elif "bullets" in item:
                    for b in item["bullets"]:
                        story.append(Paragraph(f"• {b}", S["bullet"]))
                    story.append(Spacer(1, 4))
                elif "exec_summary" in item:
                    story.append(Paragraph(item["exec_summary"],
                                           S["exec_summary_box"]))
                elif "h2" in item:
                    story.append(Paragraph(item["h2"], S["h2"]))
            else:
                story.append(item)   # raw flowable

        story.append(Spacer(1, 6))

    doc.build(story)
    print(f"  ✓  {os.path.relpath(filepath, BASE_DIR)}")


# ════════════════════════════════════════════════════════════════════════════════
#  ENGINEERING DOCUMENTS
# ════════════════════════════════════════════════════════════════════════════════

def eng_01_fastapi_architecture():
    return {
        "filename": "fastapi_architecture_guide.pdf",
        "title":    "FastAPI Architecture Guide — NovaTech Internal Platform",
        "author":   "Arjun Mehta",
        "department": "Engineering",
        "classification": "public",
        "date":     "2026-04-10",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This guide defines the canonical FastAPI architecture adopted by NovaTech's "
                    "Platform Engineering team as of Q1 2026. It covers project layout, dependency "
                    "injection patterns, middleware stack, async database access, and integration "
                    "with our Qdrant-based vector search layer. All new microservices under "
                    "Project Atlas must conform to this specification."
                )}
            ]},
            {"heading": "1. Project Layout", "content": [
                ("NovaTech standardises on a domain-driven layout for every FastAPI service. "
                 "The top-level package is split into <b>routers</b>, <b>services</b>, "
                 "<b>repositories</b>, <b>schemas</b>, and <b>core</b>. The <i>core</i> module "
                 "hosts settings (via Pydantic BaseSettings), logging configuration, and the "
                 "lifespan context manager that initialises shared resources such as the async "
                 "SQLAlchemy engine and the Qdrant AsyncClient."),
                ("All route handlers are thin orchestration layers. Business logic lives "
                 "exclusively in service classes, which are injected via FastAPI's "
                 "<b>Depends()</b> mechanism. This separation has reduced average handler "
                 "complexity from 47 lines to 12 lines across the four services migrated in Q4 "
                 "2025 (Gateway, Embedder, Retriever, Reranker)."),
                {"table": (
                    ["Layer", "Responsibility", "Owner"],
                    [
                        ["Router",     "HTTP binding, request validation", "Platform Team"],
                        ["Service",    "Business logic, orchestration",    "Domain Team"],
                        ["Repository", "DB / vector store access",         "Platform Team"],
                        ["Schema",     "Pydantic I/O models",              "Domain Team"],
                        ["Core",       "Config, logging, lifespan",        "Platform Team"],
                    ],
                    [1.5*inch, 3*inch, 1.5*inch]
                )},
            ]},
            {"heading": "2. Middleware Stack", "content": [
                ("The standard middleware order, outermost first, is: <b>CorrelationIDMiddleware</b> → "
                 "<b>RequestLoggingMiddleware</b> → <b>AuthMiddleware</b> → "
                 "<b>RateLimitMiddleware</b> → <b>CompressionMiddleware</b>."),
                ("The AuthMiddleware validates JWTs issued by our Keycloak instance and attaches "
                 "a <i>RequestContext</i> object to <i>request.state</i>. This context carries "
                 "the user's role set, tenant ID, and a pre-computed permission bitmap used by "
                 "the RBAC enforcement layer in Project Atlas's retrieval service."),
                {"bullets": [
                    "CorrelationID is propagated via X-Correlation-ID header to downstream calls.",
                    "Rate limiting uses a Redis sliding-window counter (1 000 rpm per API key by default).",
                    "Response compression is applied for payloads larger than 4 KB (gzip, level 6).",
                    "Auth token verification uses python-jose with RS256; public keys are cached for 5 minutes.",
                ]},
            ]},
            {"heading": "3. Async Database Patterns", "content": [
                ("All database I/O uses SQLAlchemy 2.0 in fully async mode with asyncpg as the "
                 "driver. Connection pool size is tuned per-service: the Query Service uses "
                 "pool_size=20, max_overflow=10, while the Ingest Service uses pool_size=5, "
                 "max_overflow=2 to avoid overwhelming the write-optimised replica."),
                ("A mandatory <b>get_db()</b> dependency yields an AsyncSession and commits or "
                 "rolls back automatically. Direct session access outside of the repository "
                 "layer is forbidden and enforced via an AST linter rule added in March 2026."),
            ]},
            {"heading": "4. Qdrant Integration", "content": [
                ("The Retriever service connects to Qdrant using the official Python async client "
                 "(qdrant-client >= 1.9). The QdrantRepository class wraps search, upsert, and "
                 "delete operations. Hybrid retrieval combines dense vectors (BAAI/bge-base-en-v1.5, "
                 "768 dims) with sparse BM25 vectors, fused via Reciprocal Rank Fusion (RRF) "
                 "with k=60."),
                ("Payload filtering enforces RBAC: each point carries a <i>classification</i> "
                 "field ('public', 'internal', 'confidential'). The must filter list is populated "
                 "at query time from the user's role set. This prevents confidential Finance "
                 "documents from appearing in results for Engineering-role users."),
            ]},
            {"heading": "5. Performance Benchmarks", "content": [
                {"table": (
                    ["Endpoint", "P50 (ms)", "P95 (ms)", "P99 (ms)", "RPS (sustained)"],
                    [
                        ["/ask (RAG)",   "210",  "480",  "820",  "340"],
                        ["/embed",       "45",   "110",  "190",  "1 200"],
                        ["/rerank",      "95",   "240",  "410",  "620"],
                        ["/health",      "2",    "5",    "9",    "8 000"],
                    ],
                    [2*inch, 1*inch, 1*inch, 1*inch, 1.5*inch]
                )},
                ("Benchmarks were run on an AWS m6i.2xlarge with 50 concurrent users using "
                 "Locust 2.24. The /ask endpoint includes Qdrant search + LLM inference; "
                 "P95 target of <500 ms is currently breached under peak load and is tracked "
                 "under Project Phoenix for Q3 2026 resolution."),
            ]},
        ],
    }


def eng_02_qdrant_deployment():
    return {
        "filename": "qdrant_deployment_strategy.pdf",
        "title":    "Qdrant Deployment Strategy — Production Cluster Guide",
        "author":   "Priya Nair",
        "department": "Engineering",
        "classification": "internal",
        "date":     "2026-03-22",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This document describes NovaTech's production deployment strategy for Qdrant "
                    "v1.10 on AWS EKS. It covers cluster sizing, collection design, backup procedures, "
                    "and the hybrid retrieval configuration powering Project Atlas's Q&A feature. "
                    "Following the March 2026 security incident, network policies and mTLS between "
                    "the API Gateway and Qdrant have been mandated."
                )}
            ]},
            {"heading": "1. Cluster Architecture", "content": [
                ("NovaTech runs a 3-node Qdrant cluster on EKS using r6g.2xlarge instances "
                 "(64 GB RAM, 8 vCPU). Each node stores a shard replica; all shards are replicated "
                 "twice for fault tolerance. The cluster serves approximately 2.4 million document "
                 "chunks ingested from Stack Overflow, Confluence, and internal PDF corpora as of "
                 "April 2026."),
                {"table": (
                    ["Collection",     "Vectors",   "Dim", "Distance",  "Payload Filters"],
                    [
                        ["eng_docs",   "840 000",   "768", "Cosine",    "dept, classification"],
                        ["prod_docs",  "620 000",   "768", "Cosine",    "dept, classification"],
                        ["conf_docs",  "180 000",   "768", "Cosine",    "dept, classification"],
                        ["stackoverflow", "760 000","768", "Cosine",    "tags, score"],
                    ],
                    [1.5*inch, 1*inch, 0.6*inch, 1*inch, 2*inch]
                )},
            ]},
            {"heading": "2. Hybrid Retrieval Configuration", "content": [
                ("Each collection stores both a <b>dense</b> vector (BAAI/bge-base-en-v1.5) and a "
                 "<b>sparse</b> BM25 vector (computed via FastEmbed's BM25 tokeniser). At query "
                 "time, Qdrant executes both searches in parallel and the Retriever service merges "
                 "results using Reciprocal Rank Fusion with k=60. Empirical tests on our internal "
                 "evaluation set show hybrid retrieval improves NDCG@10 by 18% over dense-only."),
                {"bullets": [
                    "Dense top-k: 40 results per query.",
                    "Sparse top-k: 40 results per query.",
                    "Post-RRF candidates: 80; passed to CrossEncoder reranker, top-5 returned.",
                    "Reranker model: BAAI/bge-reranker-base, served on a g4dn.xlarge GPU node.",
                ]},
            ]},
            {"heading": "3. Backup and Recovery", "content": [
                ("Qdrant snapshots are taken every 6 hours using the /snapshots REST API and "
                 "uploaded to s3://novatech-qdrant-backups/. The snapshot Lambda function was "
                 "introduced after the March 2026 security incident revealed a 14-hour gap in "
                 "recovery point objective coverage."),
                ("Restore SLA: < 2 hours for a full cluster restore from S3 snapshot, validated "
                 "quarterly via Game Day exercises. Last Game Day: 2026-04-05, restore time: 1h 44m."),
            ]},
            {"heading": "4. Security Hardening (Post March 2026 Incident)", "content": [
                ("Following the unauthorised read access discovered in March 2026, the following "
                 "controls were implemented within 72 hours: mTLS enforced on all inter-pod "
                 "communication, Qdrant API key rotated, Kubernetes NetworkPolicy restricting "
                 "Qdrant port 6333 to the Retriever service namespace only."),
                {"bullets": [
                    "mTLS via cert-manager with 90-day certificate rotation.",
                    "Qdrant API key stored in AWS Secrets Manager; rotated every 30 days.",
                    "Network Policy: only retriever-svc pods in retriever-ns may reach qdrant:6333.",
                    "Audit logging enabled; logs shipped to CloudWatch Logs with 90-day retention.",
                ]},
            ]},
        ],
    }


def eng_03_redis_caching():
    return {
        "filename": "redis_caching_design.pdf",
        "title":    "Redis Caching Design — API Gateway & Semantic Cache Layer",
        "author":   "Rohan Verma",
        "department": "Engineering",
        "classification": "internal",
        "date":     "2026-02-14",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This document specifies the Redis caching strategy for NovaTech's API Gateway "
                    "and the new semantic cache layer introduced in Project Atlas v2.1. The API "
                    "Gateway caches authentication tokens in Redis with a TTL of 15 minutes; internal "
                    "benchmarks showed a 42% reduction in PostgreSQL read load after rollout. A "
                    "semantic cache, keyed on embedding similarity, cuts LLM inference costs by "
                    "approximately 31% for repeated or near-duplicate queries."
                )}
            ]},
            {"heading": "1. Redis Topology", "content": [
                ("Production runs a 3-node Redis Cluster (ElastiCache r7g.large) with 1 primary "
                 "and 1 replica per shard, spread across 3 AZs. Cluster mode is enabled with 3 "
                 "shards, providing 18 GB total memory and automatic failover within 60 seconds."),
                {"table": (
                    ["Cache Namespace",  "TTL",   "Eviction Policy", "Est. Key Count"],
                    [
                        ["auth:tokens",   "15 min", "volatile-lru",   "40 000"],
                        ["embed:cache",   "24 h",   "volatile-lru",   "500 000"],
                        ["sem:cache",     "6 h",    "volatile-lfu",   "80 000"],
                        ["rate:limit",    "1 min",  "volatile-ttl",   "120 000"],
                        ["session:ctx",   "30 min", "volatile-lru",   "25 000"],
                    ],
                    [2*inch, 1*inch, 1.5*inch, 1.5*inch]
                )},
            ]},
            {"heading": "2. Semantic Cache Design", "content": [
                ("The semantic cache stores (query_embedding → {response, source_chunks}) pairs. "
                 "On every /ask request, the Retriever computes the query embedding and performs "
                 "a nearest-neighbour lookup in a dedicated Qdrant collection (<i>sem_cache</i>) "
                 "with a cosine similarity threshold of 0.96. A hit bypasses the full RAG pipeline "
                 "and returns the cached response in <15 ms vs the normal 210 ms median."),
                ("Cache write-back uses a Celery background task to avoid blocking the request "
                 "path. The task serialises the response, source chunk IDs, and timestamp to Redis "
                 "using MessagePack encoding (saves ~35% vs JSON for our payload shapes)."),
            ]},
            {"heading": "3. Token Cache Deep Dive", "content": [
                ("Keycloak-issued JWTs are validated at the AuthMiddleware and stored in Redis as "
                 "HASH structures: key = auth:token:{sha256(token)}, fields = user_id, roles, "
                 "tenant_id, exp. This avoids repeated RS256 signature verification and Keycloak "
                 "introspection calls. Benchmark: 0.8 ms (Redis hit) vs 38 ms (Keycloak round-trip)."),
                {"bullets": [
                    "Cache is invalidated on token revocation via a pub/sub channel: auth:revoke.",
                    "Revocation events are published by the Auth Service when a user logs out or is suspended.",
                    "Cold start: first request after deployment always hits Keycloak; warm-up completes in ~30s.",
                ]},
            ]},
            {"heading": "4. Monitoring & Alerting", "content": [
                ("Cache hit rates are published as Prometheus metrics (redis_hit_ratio) and "
                 "displayed on the NovaTech Ops Grafana dashboard. Alerting rules: hit ratio < "
                 "0.70 for auth:tokens over 5 minutes triggers a PagerDuty P2. Eviction rate "
                 "> 5 000/s triggers a capacity review."),
            ]},
        ],
    }


def eng_04_celery_jobs():
    return {
        "filename": "celery_background_jobs.pdf",
        "title":    "Celery Background Jobs — Design & Operational Guide",
        "author":   "Sneha Kapoor",
        "department": "Engineering",
        "classification": "internal",
        "date":     "2026-01-30",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "NovaTech's Celery fleet processes document ingestion, embedding generation, "
                    "reindex triggers, and async notification pipelines. This guide covers broker "
                    "configuration, task routing, retry strategies, Dead Letter Queue handling, "
                    "and the Project Phoenix migration to Celery Beat for scheduled ingestion jobs."
                )}
            ]},
            {"heading": "1. Broker & Backend Configuration", "content": [
                ("Celery uses Redis (ElastiCache) as both broker and result backend. Task messages "
                 "are published to <i>task</i> exchange with per-queue routing keys. The result "
                 "backend uses Redis with a 24-hour TTL for task state storage."),
                {"table": (
                    ["Queue",         "Concurrency", "Priority", "Workers (ECS Tasks)"],
                    [
                        ["ingest",    "4",           "High",     "8"],
                        ["embed",     "2",           "High",     "12"],
                        ["rerank",    "8",           "Medium",   "4"],
                        ["notify",    "16",          "Low",      "2"],
                        ["dlq",       "1",           "Low",      "1"],
                    ],
                    [1.5*inch, 1.2*inch, 1.2*inch, 2.1*inch]
                )},
            ]},
            {"heading": "2. Retry & DLQ Strategy", "content": [
                ("All tasks use exponential backoff: max_retries=5, countdown=2**attempt*10 (10s, "
                 "20s, 40s, 80s, 160s). After exhausting retries, the task serialises its args and "
                 "kwargs to the <b>dlq</b> queue with an error_reason field. A Celery Beat job "
                 "runs daily at 02:00 UTC to report DLQ depth to the #eng-alerts Slack channel."),
                {"bullets": [
                    "Embed tasks: idempotent; safe to retry with same chunk_id.",
                    "Ingest tasks: use a distributed lock (Redis SET NX) to prevent double-ingest.",
                    "Notify tasks: at-most-once delivery; no retry on 4xx errors from notification providers.",
                ]},
            ]},
            {"heading": "3. Project Phoenix Integration", "content": [
                ("Project Phoenix (Q3 2026) consolidates four separate cron-based ingestion "
                 "scripts into a unified Celery Beat schedule. The new schedule includes: "
                 "hourly Confluence crawl, 6-hourly PDF corpus scan, daily Stack Overflow "
                 "data refresh, and weekly Qdrant index optimisation. This eliminates 1 200+ "
                 "lines of bespoke scheduler code and provides a single pane of glass in Flower."),
            ]},
            {"heading": "4. Observability", "content": [
                ("Flower is deployed as an internal-only service (no public ingress) on port 5555. "
                 "Each task emits structured logs (task_id, queue, attempt, duration_ms) to "
                 "CloudWatch. A custom Grafana dashboard tracks task throughput, failure rate, "
                 "and P95 queue wait time per queue. SLA: embed queue P95 wait < 30 seconds."),
            ]},
        ],
    }


def eng_05_api_versioning():
    return {
        "filename": "api_versioning_policy.pdf",
        "title":    "API Versioning Policy — NovaTech Platform Engineering",
        "author":   "Kiran Desai",
        "department": "Engineering",
        "classification": "public",
        "date":     "2026-03-05",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This policy defines how NovaTech versions its public and internal REST APIs. "
                    "It mandates URL-path versioning (/v1/, /v2/), deprecation timelines, and "
                    "sunset header usage. Non-compliance blocks production deploys via the CI/CD "
                    "pipeline policy gate introduced in February 2026."
                )}
            ]},
            {"heading": "1. Versioning Scheme", "content": [
                ("NovaTech uses URI versioning: /api/v{MAJOR}/. Minor, backward-compatible changes "
                 "are deployed without a version bump. Breaking changes (removed fields, changed "
                 "semantics, new required parameters) require a new MAJOR version."),
                {"bullets": [
                    "v1: GA as of 2024-09-01. Supported until 2027-09-01 (3-year minimum lifecycle).",
                    "v2: GA as of 2026-01-15. Introduces async streaming responses and pagination cursors.",
                    "v3: In development under Project Atlas; targets GA in Q4 2026.",
                ]},
            ]},
            {"heading": "2. Deprecation Process", "content": [
                ("Deprecated endpoints must emit a <b>Deprecation</b> header "
                 "(RFC 8594) and a <b>Sunset</b> header 180 days before removal. "
                 "The API changelog at /changelog must be updated within 24 hours of deprecation "
                 "announcement."),
                {"table": (
                    ["Deprecation Stage", "Action Required",              "Timeline"],
                    [
                        ["Announced",  "Deprecation + Sunset headers set",  "D+0"],
                        ["Warning",    "Weekly email to registered consumers","D+90"],
                        ["Critical",   "Daily email + Slack #api-deprecations","D+150"],
                        ["Sunset",     "Endpoint removed, returns 410 Gone", "D+180"],
                    ],
                    [1.8*inch, 2.8*inch, 1.4*inch]
                )},
            ]},
            {"heading": "3. Contract Testing", "content": [
                ("Every API version change triggers a Pact contract test suite in CI. Consumers "
                 "publish their Pact files to the NovaTech Pact Broker; providers verify against "
                 "all registered consumer contracts before merging. Failures block the merge queue."),
            ]},
        ],
    }


def eng_06_observability():
    return {
        "filename": "observability_and_monitoring.pdf",
        "title":    "Observability & Monitoring — NovaTech Platform Standards",
        "author":   "Ananya Krishnan",
        "department": "Engineering",
        "classification": "internal",
        "date":     "2026-04-01",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "NovaTech adopts the three pillars of observability: metrics (Prometheus + "
                    "Grafana), traces (Tempo + OpenTelemetry), and logs (CloudWatch + structured "
                    "JSON). This document specifies instrumentation standards, SLO definitions, "
                    "alerting runbooks, and the post-March 2026 incident improvements to detection "
                    "latency."
                )}
            ]},
            {"heading": "1. Metrics Standards", "content": [
                ("All services must expose a /metrics endpoint in Prometheus exposition format. "
                 "Required metrics: http_request_duration_seconds (histogram), "
                 "http_requests_total (counter by method/status), and process_resident_memory_bytes. "
                 "Custom business metrics (e.g., rag_retrieval_ndcg, embed_cache_hit_ratio) are "
                 "defined in a shared metrics registry in the novatech-shared-libs package."),
                {"table": (
                    ["SLO",                       "Target",   "Alert Window", "Severity"],
                    [
                        ["API Availability",       "99.9%",    "5 min",        "P1"],
                        ["/ask P95 Latency",       "<500ms",   "10 min",       "P2"],
                        ["Embed Queue P95 Wait",   "<30s",     "5 min",        "P2"],
                        ["Qdrant Search P99",      "<200ms",   "5 min",        "P1"],
                        ["Error Rate",             "<0.5%",    "5 min",        "P2"],
                    ],
                    [2.5*inch, 1*inch, 1.3*inch, 1*inch]
                )},
            ]},
            {"heading": "2. Distributed Tracing", "content": [
                ("OpenTelemetry SDK (Python) is integrated via middleware into every FastAPI "
                 "service. Traces are exported to AWS Managed Grafana Tempo. Sampling rate: "
                 "100% for error traces, 5% for success traces in production. Trace context is "
                 "propagated via W3C TraceContext headers."),
                ("The March 2026 security incident was partially obscured because the Qdrant "
                 "client was not instrumented with OTel. As of April 2026, all Qdrant calls emit "
                 "spans with collection_name, operation, and duration_ms attributes."),
            ]},
            {"heading": "3. Log Standards", "content": [
                ("All logs must be structured JSON with mandatory fields: timestamp (ISO 8601), "
                 "level, service, correlation_id, user_id (hashed), message. PII must never "
                 "appear in logs; a log scrubber middleware strips email, phone, and IP fields "
                 "before emission."),
                {"bullets": [
                    "Log levels: DEBUG (dev only), INFO (business events), WARNING (degraded state), ERROR (failed operations).",
                    "Retention: INFO and above retained 90 days in CloudWatch; ERROR retained 1 year.",
                    "Log-based alerts: ERROR rate > 10/min over 2 minutes triggers PagerDuty P2.",
                ]},
            ]},
        ],
    }


def eng_07_kubernetes():
    return {
        "filename": "kubernetes_deployment_guide.pdf",
        "title":    "Kubernetes Deployment Guide — EKS Production Clusters",
        "author":   "Vikram Sharma",
        "department": "Engineering",
        "classification": "public",
        "date":     "2026-02-20",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This guide documents NovaTech's EKS cluster configuration, namespace "
                    "conventions, resource quotas, HPA/KEDA autoscaling policies, and the "
                    "GitOps deployment workflow via ArgoCD. All Project Atlas services must be "
                    "deployed using the novatech-helm-chart base chart with mandatory security "
                    "contexts and network policies."
                )}
            ]},
            {"heading": "1. Cluster Layout", "content": [
                ("Production runs two EKS clusters: <b>us-east-1 (primary)</b> and "
                 "<b>eu-west-1 (DR)</b>. Node groups are split by workload: "
                 "compute-optimised (c6i.4xlarge) for CPU-bound services, memory-optimised "
                 "(r6g.2xlarge) for Qdrant and Redis, and GPU (g4dn.xlarge) for the reranker "
                 "and embedding inference services."),
                {"table": (
                    ["Namespace",       "Services",                   "Resource Quota (CPU/Mem)"],
                    [
                        ["retriever",   "retriever-api, qdrant",      "32 / 128 Gi"],
                        ["embed",       "embedder-svc, celery-embed",  "64 / 64 Gi"],
                        ["gateway",     "api-gateway, auth-proxy",     "16 / 32 Gi"],
                        ["monitoring",  "prometheus, grafana, tempo",  "8 / 16 Gi"],
                        ["ingress",     "nginx-ingress, cert-manager", "4 / 8 Gi"],
                    ],
                    [1.5*inch, 2.3*inch, 2.2*inch]
                )},
            ]},
            {"heading": "2. Autoscaling", "content": [
                ("CPU-bound services use HPA with target CPU utilisation of 65%. "
                 "The Celery worker fleet uses KEDA with a Redis queue-length trigger: "
                 "1 worker per 50 pending tasks, min=2, max=20 per queue. "
                 "Qdrant and stateful services are not autoscaled; capacity is provisioned "
                 "via quarterly capacity planning reviews."),
            ]},
            {"heading": "3. Security Contexts", "content": [
                ("All pods must run as non-root (runAsNonRoot: true, runAsUser: 1000). "
                 "Read-only root filesystems are enforced for stateless services. "
                 "Privileged containers are blocked by OPA Gatekeeper policy. "
                 "Image signatures are verified via Cosign before deployment."),
                {"bullets": [
                    "Pod Security Standards: Restricted profile enforced cluster-wide.",
                    "Network Policies: deny-all default; explicit allow rules per namespace.",
                    "Secrets: all environment secrets sourced from AWS Secrets Manager via ESO.",
                    "Image scanning: Trivy scans all images in CI; HIGH CVEs block merge.",
                ]},
            ]},
        ],
    }


def eng_08_cicd():
    return {
        "filename": "cicd_pipeline_standards.pdf",
        "title":    "CI/CD Pipeline Standards — NovaTech Engineering",
        "author":   "Meera Pillai",
        "department": "Engineering",
        "classification": "public",
        "date":     "2026-03-18",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This document defines the mandatory CI/CD pipeline stages, quality gates, "
                    "and deployment strategies for all NovaTech services. GitHub Actions is the "
                    "standard CI platform. ArgoCD manages GitOps-style continuous deployment to "
                    "EKS. All pipelines must pass the security, contract, and performance gates "
                    "before reaching production."
                )}
            ]},
            {"heading": "1. Pipeline Stages", "content": [
                {"table": (
                    ["Stage",            "Tool",           "Pass Criteria",              "SLA"],
                    [
                        ["Lint & Format", "Ruff, Black",    "Zero violations",            "< 2 min"],
                        ["Unit Tests",    "pytest",         "Coverage >= 85%",            "< 5 min"],
                        ["Security Scan", "Trivy, Bandit",  "No HIGH/CRIT CVEs",          "< 3 min"],
                        ["Contract Tests","Pact",           "All consumer pacts green",   "< 4 min"],
                        ["Build & Push",  "Docker, ECR",    "Image signed via Cosign",    "< 6 min"],
                        ["Perf Gate",     "k6",             "P95 < 500ms at 100 RPS",     "< 8 min"],
                        ["Deploy (Staging)","ArgoCD",       "Health checks green",        "< 10 min"],
                        ["Deploy (Prod)",  "ArgoCD",        "Canary 5%→25%→100%",        "< 20 min"],
                    ],
                    [1.8*inch, 1.4*inch, 2*inch, 1*inch]
                )},
            ]},
            {"heading": "2. Deployment Strategy", "content": [
                ("Production deployments use a canary strategy: 5% traffic for 10 minutes, "
                 "then 25% for 10 minutes, then 100% if error rate remains below 0.5% and "
                 "P95 latency stays below 500 ms. Automated rollback triggers if either "
                 "threshold is breached during the canary phase."),
                ("Feature flags (LaunchDarkly) are used to decouple deploy from release. "
                 "Project Atlas features default to off in production and are enabled per "
                 "tenant by the Product team after internal testing."),
            ]},
            {"heading": "3. Secrets Management in CI", "content": [
                ("No secrets may be stored in GitHub repository secrets for production "
                 "environments. CI workflows use OIDC to assume an IAM role and fetch "
                 "secrets from AWS Secrets Manager at runtime. Staging uses a dedicated "
                 "IAM role with scoped permissions."),
            ]},
        ],
    }


def eng_09_vector_search():
    return {
        "filename": "vector_search_best_practices.pdf",
        "title":    "Vector Search Best Practices — Embedding & Retrieval Guide",
        "author":   "Rahul Gupta",
        "department": "Engineering",
        "classification": "public",
        "date":     "2026-04-15",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This guide consolidates NovaTech's hard-won lessons from deploying vector "
                    "search at scale for Project Atlas. It covers embedding model selection, "
                    "chunking strategies, HNSW index tuning, hybrid retrieval design, and "
                    "evaluation metrics. Teams using Qdrant must review this guide before "
                    "creating new collections."
                )}
            ]},
            {"heading": "1. Embedding Model Selection", "content": [
                ("After evaluating 8 embedding models on our internal benchmark (3 200 query-"
                 "document pairs), BAAI/bge-base-en-v1.5 (768 dims) was selected as the "
                 "standard dense model. It achieved the best NDCG@10 score (0.74) while "
                 "remaining deployable on CPU for batch inference."),
                {"table": (
                    ["Model",                   "NDCG@10", "Latency (ms)", "Dims", "Decision"],
                    [
                        ["BAAI/bge-base-en-v1.5",  "0.74",  "45",   "768",  "Selected"],
                        ["text-embedding-3-small",  "0.72",  "110",  "1536", "Rejected (cost)"],
                        ["all-MiniLM-L6-v2",        "0.61",  "12",   "384",  "Rejected (quality)"],
                        ["BAAI/bge-large-en-v1.5",  "0.76",  "210",  "1024", "Rejected (latency)"],
                    ],
                    [2.4*inch, 1*inch, 1.2*inch, 0.7*inch, 1.3*inch]
                )},
            ]},
            {"heading": "2. Chunking Strategy", "content": [
                ("Documents are chunked using a recursive character splitter with "
                 "chunk_size=512 tokens, chunk_overlap=64 tokens. Sentence boundaries are "
                 "respected via a sentence-aware split that never breaks mid-sentence. "
                 "Metadata (title, section heading, page number, classification) is stored "
                 "as Qdrant payload alongside each chunk."),
                {"bullets": [
                    "Code blocks are chunked separately with a max size of 1 024 tokens.",
                    "Tables are extracted as standalone chunks with a table prefix in the text.",
                    "Short chunks < 50 tokens are merged with the next sibling chunk.",
                    "Parent-child chunking is used for context window expansion in reranking.",
                ]},
            ]},
            {"heading": "3. HNSW Index Tuning", "content": [
                ("Production Qdrant collections use m=16, ef_construct=200 for index build, "
                 "and ef=128 for search. These values were selected via a grid search balancing "
                 "recall@10 (>0.97 target) and memory usage. Increasing m beyond 16 improved "
                 "recall by only 0.4% while doubling index size."),
            ]},
            {"heading": "4. Evaluation Framework", "content": [
                ("Retrieval quality is measured weekly using RAGAS: faithfulness, answer "
                 "relevance, context precision, and context recall. Scores are tracked in "
                 "a Grafana panel. A drop of more than 0.05 in any metric over 7 days "
                 "triggers a retrieval review meeting."),
            ]},
        ],
    }


def eng_10_rag_architecture():
    return {
        "filename": "rag_system_architecture.pdf",
        "title":    "RAG System Architecture — Project Atlas Technical Specification",
        "author":   "Deepa Iyer",
        "department": "Engineering",
        "classification": "internal",
        "date":     "2026-04-20",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This document is the authoritative technical specification for the "
                    "Retrieval-Augmented Generation system powering Project Atlas. It covers "
                    "the end-to-end pipeline from query ingestion to cited response generation, "
                    "the RBAC enforcement model, multi-collection routing, and the evaluation "
                    "harness. The system went into private beta on 2026-03-01 and is on track "
                    "for GA in Q3 2026 per the Product roadmap."
                )}
            ]},
            {"heading": "1. Pipeline Overview", "content": [
                ("The /ask endpoint accepts a query string and optional filters (department, "
                 "classification). The pipeline: (1) validate RBAC — strip collections the "
                 "user cannot access; (2) embed query with BAAI/bge-base-en-v1.5; (3) run "
                 "hybrid search (dense + BM25) against permitted Qdrant collections; (4) fuse "
                 "results with RRF k=60; (5) rerank top-20 with BAAI/bge-reranker-base; "
                 "(6) pass top-5 chunks to Claude claude-sonnet-4-6 with a citation prompt; "
                 "(7) stream response."),
            ]},
            {"heading": "2. RBAC Enforcement", "content": [
                ("Users are assigned roles: <b>eng</b>, <b>product</b>, <b>exec</b>. "
                 "Each role maps to permitted Qdrant collections and payload filter "
                 "classifications. The mapping is stored in the AuthService and injected "
                 "into the RequestContext at authentication time."),
                {"table": (
                    ["Role",    "Permitted Collections",          "Classifications"],
                    [
                        ["eng",     "eng_docs, stackoverflow",    "public, internal"],
                        ["product", "prod_docs, eng_docs",        "public, internal"],
                        ["exec",    "all collections",            "public, internal, confidential"],
                    ],
                    [1*inch, 2.8*inch, 2.2*inch]
                )},
            ]},
            {"heading": "3. Citation Generation", "content": [
                ("The LLM prompt instructs the model to cite each factual claim with "
                 "[Doc N] notation, where N corresponds to the source chunk index passed "
                 "in the context. The API response includes a sources array with "
                 "doc_id, title, section, page, classification, and similarity_score "
                 "for each cited chunk."),
            ]},
            {"heading": "4. Evaluation Harness", "content": [
                ("The RAGAS evaluation suite runs against a 200-question golden dataset "
                 "every Sunday at 03:00 UTC. Results are committed to the eval-results "
                 "repository and surfaced on the Atlas Engineering dashboard. Current "
                 "scores: faithfulness=0.89, answer_relevance=0.86, context_precision=0.82, "
                 "context_recall=0.79. Target for GA: all metrics > 0.85."),
                {"bullets": [
                    "Faithfulness measures whether all claims in the answer are supported by the context.",
                    "Answer relevance measures alignment of the answer with the original question.",
                    "Context precision measures what fraction of retrieved chunks are actually relevant.",
                    "Context recall measures coverage — are all relevant chunks being retrieved?",
                ]},
            ]},
        ],
    }


# ════════════════════════════════════════════════════════════════════════════════
#  PRODUCT DOCUMENTS
# ════════════════════════════════════════════════════════════════════════════════

def prod_01_roadmap():
    return {
        "filename": "product_roadmap_q3_2026.pdf",
        "title":    "Product Roadmap — Q3 2026",
        "author":   "Nalini Bose",
        "department": "Product",
        "classification": "internal",
        "date":     "2026-04-25",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This document outlines NovaTech's product roadmap for Q3 2026 (July–September). "
                    "Key themes are the general availability launch of Project Atlas, the rollout of "
                    "advanced analytics for enterprise customers, and Project Phoenix's transition to "
                    "a self-serve onboarding experience. Feature X (multi-document Q&A) is scheduled "
                    "to launch in July 2026 pending successful Q2 beta."
                )}
            ]},
            {"heading": "1. Q3 2026 Themes", "content": [
                {"bullets": [
                    "Theme 1: GA launch of Project Atlas (AI Q&A on enterprise knowledge bases).",
                    "Theme 2: Enterprise Analytics Dashboard — usage metrics, retrieval quality KPIs.",
                    "Theme 3: Project Phoenix self-serve onboarding (zero-touch setup for SMB tier).",
                    "Theme 4: Compliance — SOC 2 Type II readiness; data residency controls (EU).",
                ]},
            ]},
            {"heading": "2. Feature Roadmap", "content": [
                {"table": (
                    ["Feature",               "Owner",        "Target Launch", "Status"],
                    [
                        ["Project Atlas GA",    "Deepa Iyer",  "July 2026",  "On Track"],
                        ["Feature X (Multi-doc Q&A)", "Nalini Bose", "July 2026", "At Risk"],
                        ["EU Data Residency",   "Kiran Desai", "Aug 2026",   "On Track"],
                        ["Analytics Dashboard", "Rohan Verma", "Aug 2026",   "On Track"],
                        ["Phoenix Self-Serve",  "Priya Nair",  "Sep 2026",   "On Track"],
                        ["SOC 2 Type II",       "Legal / Eng", "Sep 2026",   "In Progress"],
                    ],
                    [2.2*inch, 1.5*inch, 1.3*inch, 1*inch]
                )},
            ]},
            {"heading": "3. Project Atlas GA Requirements", "content": [
                ("Project Atlas cannot enter GA until the following gates are passed: "
                 "RAGAS faithfulness > 0.85, P95 /ask latency < 500 ms, security review "
                 "sign-off (post March 2026 incident remediation complete), and SOC 2 "
                 "readiness assessment green."),
            ]},
            {"heading": "4. Risks & Mitigations", "content": [
                {"bullets": [
                    "Feature X latency under multi-document load exceeds 500ms — GPU scaling investigation underway.",
                    "SOC 2 audit delayed by 3 weeks — may push GA to early August if not resolved.",
                    "Qdrant cluster capacity may need expansion before Q3 peak; provisioning in progress.",
                ]},
            ]},
        ],
    }


def prod_02_pricing():
    return {
        "filename": "pricing_strategy_2026.pdf",
        "title":    "Pricing Strategy 2026 — NovaTech SaaS Tiers",
        "author":   "Suresh Iyer",
        "department": "Product",
        "classification": "public",
        "date":     "2026-03-10",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This document defines NovaTech's 2026 pricing architecture for the Atlas "
                    "platform. Three tiers are proposed: Starter ($49/mo), Growth ($299/mo), and "
                    "Enterprise (custom). The shift from per-seat to usage-based pricing (per-query) "
                    "for the Growth tier reflects feedback from 14 customer discovery interviews "
                    "conducted in February 2026."
                )}
            ]},
            {"heading": "1. Pricing Tiers", "content": [
                {"table": (
                    ["Tier",       "Price",          "Queries/mo", "Docs",    "RBAC", "Support"],
                    [
                        ["Starter",   "$49/mo",         "1 000",   "500",     "No",   "Email"],
                        ["Growth",    "$299/mo",         "10 000",  "10 000",  "Yes",  "Chat"],
                        ["Enterprise","Custom",          "Unlimited","Unlimited","Yes", "Dedicated"],
                    ],
                    [1.1*inch, 1.1*inch, 1.1*inch, 1.1*inch, 0.8*inch, 1.4*inch]
                )},
            ]},
            {"heading": "2. Pricing Rationale", "content": [
                ("Competitive analysis (see Competitive Analysis document) shows primary "
                 "competitors charging $0.04–$0.08 per query for comparable RAG APIs. "
                 "NovaTech targets $0.03/query at Growth tier volume, implying a contribution "
                 "margin of 58% after LLM and infrastructure costs."),
                ("Enterprise deals are priced on a 3-year TCO basis with volume discounts "
                 "starting at 15% for >500 000 queries/mo. The Project Atlas enterprise "
                 "pilot with FinCorp (signed March 2026) is priced at $48 000/year for "
                 "1.2M queries/mo."),
            ]},
            {"heading": "3. Usage Overages", "content": [
                ("Starter and Growth tiers incur overage charges of $0.06/query beyond "
                 "the included allowance. Overage billing is capped at 2× the base plan "
                 "price per month to prevent bill shock. Customers are notified at 80% "
                 "and 100% of their monthly allowance via email."),
            ]},
        ],
    }


def prod_03_customer_feedback():
    return {
        "filename": "customer_feedback_analysis_q1_2026.pdf",
        "title":    "Customer Feedback Analysis — Q1 2026",
        "author":   "Kavitha Ramesh",
        "department": "Product",
        "classification": "internal",
        "date":     "2026-04-05",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "Analysis of 847 NPS responses, 34 customer interviews, and 1 200 in-app "
                    "feedback submissions collected in Q1 2026. Overall NPS improved from 31 "
                    "to 44. Top requested features: multi-document Q&A (Feature X), Slack "
                    "integration, and role-based access for shared workspaces. Project Atlas "
                    "beta users report 91% satisfaction with answer quality."
                )}
            ]},
            {"heading": "1. NPS Trend", "content": [
                {"table": (
                    ["Quarter", "Promoters", "Passives", "Detractors", "NPS"],
                    [
                        ["Q3 2025", "41%", "21%", "38%", "3"],
                        ["Q4 2025", "48%", "24%", "28%", "20"],
                        ["Q1 2026", "62%", "20%", "18%", "44"],
                    ],
                    [1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch]
                )},
            ]},
            {"heading": "2. Top Requested Features", "content": [
                {"bullets": [
                    "Multi-document Q&A (Feature X): 68% of Growth customers — top priority.",
                    "Slack integration: 54% of Enterprise prospects mention during sales calls.",
                    "RBAC for shared workspaces: 47% of team-account customers.",
                    "EU data residency: 31% of European pipeline deals cite as a blocker.",
                    "Custom embedding model support: 22% of technical users.",
                ]},
            ]},
            {"heading": "3. Project Atlas Beta Feedback", "content": [
                ("34 beta users from 8 enterprise accounts participated in the Q1 pilot. "
                 "91% rated answer quality as 'good' or 'excellent'. Main complaints: "
                 "response latency (avg 2.1s perceived), lack of source document preview, "
                 "and no ability to ask follow-up questions in context."),
                ("Qdrant-powered retrieval was praised by 3 engineering-heavy accounts who "
                 "noted answer accuracy significantly exceeded their previous keyword-search "
                 "solutions. One customer (TechRetail) reported a 3× reduction in support "
                 "ticket escalations after deploying Atlas on their internal knowledge base."),
            ]},
        ],
    }


def prod_04_feature_prioritization():
    return {
        "filename": "feature_prioritization_framework.pdf",
        "title":    "Feature Prioritization Framework — RICE Scoring Model",
        "author":   "Nalini Bose",
        "department": "Product",
        "classification": "internal",
        "date":     "2026-03-28",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "NovaTech's Product team uses a RICE scoring model (Reach × Impact × Confidence "
                    "/ Effort) to prioritise the feature backlog. This document defines the scoring "
                    "rubric, governance process, and Q2/Q3 2026 prioritisation outcomes. Feature X "
                    "received the highest RICE score in the Q3 cycle (score: 84), ahead of the "
                    "Slack Integration (score: 71) and EU Data Residency (score: 68)."
                )}
            ]},
            {"heading": "1. RICE Scoring Rubric", "content": [
                {"table": (
                    ["Dimension",  "Definition",                          "Scale"],
                    [
                        ["Reach",     "# customers affected per quarter",     "1–1000"],
                        ["Impact",    "Improvement to key metric (revenue/NPS)","0.25/0.5/1/2/3"],
                        ["Confidence","Evidence strength for estimates",       "20%/50%/80%/100%"],
                        ["Effort",    "Person-months of engineering work",     "0.5–12"],
                    ],
                    [1.2*inch, 3.2*inch, 1.8*inch]
                )},
            ]},
            {"heading": "2. Q3 2026 Feature Scores", "content": [
                {"table": (
                    ["Feature",           "Reach", "Impact", "Conf.", "Effort", "RICE"],
                    [
                        ["Feature X",       "450",  "2",    "80%",  "8.5",   "84"],
                        ["Slack Integration","380",  "1",    "80%",  "4",     "71"],
                        ["EU Residency",     "200",  "3",    "80%",  "7",     "68"],
                        ["Analytics Dash",   "600",  "1",    "100%", "6",     "100"],
                        ["Custom Embeddings","120",  "2",    "50%",  "7",     "17"],
                    ],
                    [2.2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch]
                )},
            ]},
            {"heading": "3. Governance Process", "content": [
                ("RICE scores are recalculated at the start of each quarter in a 2-hour "
                 "Product Council meeting attended by the CPO, VPs of Engineering and Sales, "
                 "and the Head of Customer Success. Scores above 50 automatically enter the "
                 "roadmap; scores 30–50 are reviewed case-by-case; scores below 30 are "
                 "parked in the idea backlog."),
            ]},
        ],
    }


def prod_05_analytics():
    return {
        "filename": "product_analytics_review_q1_2026.pdf",
        "title":    "Product Analytics Review — Q1 2026",
        "author":   "Arun Balachandran",
        "department": "Product",
        "classification": "internal",
        "date":     "2026-04-08",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "Q1 2026 saw 34% growth in Monthly Active Users (MAU) to 12 400, driven by "
                    "the Project Atlas private beta and a January 2026 Product Hunt launch. "
                    "Query volume reached 4.2M/month, up from 2.8M in Q4 2025. Day-30 retention "
                    "improved from 38% to 51% following the onboarding flow redesign shipped in "
                    "February 2026."
                )}
            ]},
            {"heading": "1. Growth Metrics", "content": [
                {"table": (
                    ["Metric",              "Q4 2025",  "Q1 2026",  "QoQ Change"],
                    [
                        ["MAU",               "9 250",   "12 400",   "+34%"],
                        ["WAU",               "5 100",   "7 800",    "+53%"],
                        ["Query Volume/mo",   "2.8M",    "4.2M",     "+50%"],
                        ["Day-7 Retention",   "58%",     "64%",      "+6pp"],
                        ["Day-30 Retention",  "38%",     "51%",      "+13pp"],
                        ["Avg Queries/User",  "302",     "339",      "+12%"],
                    ],
                    [2.2*inch, 1.2*inch, 1.2*inch, 1.4*inch]
                )},
            ]},
            {"heading": "2. Qdrant-Powered Query Quality", "content": [
                ("After migrating from keyword search to Qdrant-based hybrid retrieval in "
                 "January 2026, the 'Answer Not Found' rate dropped from 18% to 6%. Users "
                 "who receive a cited answer have a 2.4× higher Day-30 retention rate than "
                 "those who receive an 'Answer Not Found' response. This validates the "
                 "investment in Project Atlas's retrieval infrastructure."),
            ]},
            {"heading": "3. Feature Adoption", "content": [
                {"bullets": [
                    "RBAC (enterprise tier): 78% of enterprise accounts have configured at least one role.",
                    "Citation display: 65% of users click through to at least one source per session.",
                    "Conversation history: 43% of WAU users use follow-up questioning.",
                    "API access: 29% of Growth accounts are API-only (no web UI usage).",
                ]},
            ]},
        ],
    }


def prod_06_market_research():
    return {
        "filename": "market_research_findings_2026.pdf",
        "title":    "Market Research Findings — Enterprise AI Search 2026",
        "author":   "Preethi Sundaram",
        "department": "Product",
        "classification": "public",
        "date":     "2026-02-28",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This report summarises findings from a 200-company survey and 20 in-depth "
                    "interviews targeting enterprise knowledge management buyers in the 500–5 000 "
                    "employee segment. The total addressable market for AI-powered enterprise "
                    "search is estimated at $4.2B in 2026, growing at 38% CAGR. Security and "
                    "data privacy are the top two purchase blockers."
                )}
            ]},
            {"heading": "1. Market Size & Growth", "content": [
                {"table": (
                    ["Segment",              "2026 TAM",  "CAGR (3yr)", "NovaTech Fit"],
                    [
                        ["SMB (< 200 emp)",   "$480M",    "29%",        "Starter/Growth"],
                        ["Mid-Market",         "$1.6B",   "38%",        "Growth/Enterprise"],
                        ["Enterprise",         "$2.1B",   "41%",        "Enterprise"],
                    ],
                    [2*inch, 1.2*inch, 1.3*inch, 1.6*inch]
                )},
            ]},
            {"heading": "2. Buying Criteria (Ranked)", "content": [
                {"bullets": [
                    "1. Data security & privacy controls (cited by 84% of respondents).",
                    "2. Answer accuracy / hallucination rate (79%).",
                    "3. Integration with existing tools (Slack, Confluence, Google Drive) (71%).",
                    "4. Total cost of ownership (65%).",
                    "5. Vendor stability and support SLA (58%).",
                ]},
            ]},
            {"heading": "3. Purchase Blockers", "content": [
                ("The March 2026 wave of enterprise AI security incidents (including one "
                 "publicly reported case involving an unnamed AI search vendor) has heightened "
                 "security scrutiny. 67% of respondents now require SOC 2 Type II certification "
                 "before procurement, up from 48% in the 2025 survey. NovaTech's SOC 2 "
                 "audit is scheduled for Q3 2026."),
            ]},
        ],
    }


def prod_07_segmentation():
    return {
        "filename": "customer_segmentation_2026.pdf",
        "title":    "Customer Segmentation Analysis — NovaTech 2026",
        "author":   "Kavitha Ramesh",
        "department": "Product",
        "classification": "internal",
        "date":     "2026-03-15",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "Analysis of NovaTech's 1 840 paying accounts reveals four distinct segments: "
                    "Developer Hobbyists (24%), Technical SMBs (38%), Mid-Market Operations (28%), "
                    "and Enterprise (10%). Enterprise accounts represent 61% of ARR despite being "
                    "10% of account count. Project Atlas adoption is highest in the Technical SMB "
                    "and Enterprise segments."
                )}
            ]},
            {"heading": "1. Segment Profiles", "content": [
                {"table": (
                    ["Segment",          "Accounts", "ARR Share", "Avg ARR",   "Atlas Adoption"],
                    [
                        ["Dev Hobbyist",  "441",      "4%",        "$410",      "12%"],
                        ["Tech SMB",      "699",      "22%",       "$1 420",    "34%"],
                        ["Mid-Market Ops","515",      "33%",       "$2 900",    "28%"],
                        ["Enterprise",    "185",      "61%",       "$15 000+",  "51%"],
                    ],
                    [1.8*inch, 1*inch, 1.1*inch, 1.2*inch, 1.5*inch]
                )},
            ]},
            {"heading": "2. Project Atlas Adoption Drivers", "content": [
                ("Enterprise and Tech SMB segments adopt Atlas at higher rates because they "
                 "have existing knowledge management infrastructure (Confluence, SharePoint) "
                 "that Atlas integrates with. Dev Hobbyist adoption is blocked by the $299/mo "
                 "Growth tier price point required for RBAC, a key Atlas feature."),
            ]},
            {"heading": "3. Expansion Opportunity", "content": [
                ("Mid-Market accounts that adopt Project Atlas have a 4.2× higher 12-month "
                 "expansion rate than non-Atlas accounts ($8 200 vs $1 950 NRR). "
                 "Prioritising Atlas enablement for the 370 eligible Mid-Market accounts "
                 "not yet using Atlas represents an estimated $2.3M ARR expansion opportunity."),
            ]},
        ],
    }


def prod_08_launch_plan():
    return {
        "filename": "product_launch_plan_atlas_ga.pdf",
        "title":    "Product Launch Plan — Project Atlas GA",
        "author":   "Nalini Bose",
        "department": "Product",
        "classification": "internal",
        "date":     "2026-04-18",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This document outlines the go-to-market plan for Project Atlas General "
                    "Availability, currently targeted for August 2026. Note: Feature X "
                    "(multi-document Q&A) is expected to launch in August alongside the Atlas GA, "
                    "pending resolution of the P95 latency issue identified in Q2 load testing. "
                    "An earlier Q3 roadmap document listed Feature X for July; the August date "
                    "reflects a 4-week slip approved in the April 2026 Product Council."
                )}
            ]},
            {"heading": "1. Launch Timeline", "content": [
                {"table": (
                    ["Milestone",                     "Date",        "Owner"],
                    [
                        ["Security review complete",   "2026-06-15",  "Security Team"],
                        ["SOC 2 audit complete",       "2026-07-01",  "Legal"],
                        ["Feature X perf gate passed", "2026-07-15",  "Eng (Deepa)"],
                        ["Docs & marketing site live", "2026-07-28",  "Marketing"],
                        ["Atlas GA + Feature X launch","2026-08-05",  "Product"],
                        ["PR / analyst briefings",     "2026-08-05",  "Marketing"],
                    ],
                    [2.5*inch, 1.4*inch, 1.8*inch]
                )},
                ("Note: An earlier version of the Q3 2026 Roadmap document listed Feature X "
                 "for July 2026. The August 2026 date is the authoritative launch date as of "
                 "the April 2026 Product Council decision. Please disregard the July date in "
                 "older planning documents."),
            ]},
            {"heading": "2. Go-To-Market Channels", "content": [
                {"bullets": [
                    "Product Hunt launch on GA day — targeting top-5 Product of the Day.",
                    "Email campaign to 28 000 beta waitlist subscribers.",
                    "Webinar series: 3 x 45-min technical deep-dives in August.",
                    "Partner channel: 4 system integrators briefed under NDA in July.",
                    "Analyst relations: Gartner and Forrester briefings scheduled 2 weeks pre-launch.",
                ]},
            ]},
        ],
    }


def prod_09_retention():
    return {
        "filename": "retention_strategy_2026.pdf",
        "title":    "Retention Strategy 2026 — Reducing Churn, Driving Expansion",
        "author":   "Arun Balachandran",
        "department": "Product",
        "classification": "internal",
        "date":     "2026-03-22",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "NovaTech's Q1 2026 monthly logo churn of 2.1% exceeds the 1.5% target. "
                    "This strategy document identifies the three primary churn drivers — "
                    "poor onboarding completion, low query volume in the first 30 days, and "
                    "lack of RBAC configuration for team accounts — and proposes mitigations "
                    "aligned with the Project Phoenix self-serve initiative."
                )}
            ]},
            {"heading": "1. Churn Analysis", "content": [
                {"table": (
                    ["Churn Driver",              "% of Churned Accounts", "Proposed Fix"],
                    [
                        ["Poor onboarding",        "44%",    "Phoenix wizard flow"],
                        ["Low 30-day query volume","31%",    "Usage nudge emails"],
                        ["RBAC not configured",    "18%",    "In-app RBAC guide"],
                        ["Price sensitivity",      "7%",     "Annual plan discount"],
                    ],
                    [2.5*inch, 2*inch, 1.8*inch]
                )},
            ]},
            {"heading": "2. Project Phoenix Self-Serve Initiative", "content": [
                ("Project Phoenix, targeting Q3 2026 launch, redesigns the onboarding "
                 "experience with a guided wizard that connects the customer's first knowledge "
                 "source (Confluence, Google Drive, or PDF upload) within 10 minutes. "
                 "Internal testing shows wizard completion rates of 87% vs 41% for the "
                 "current freeform setup."),
                ("The wizard automatically suggests RBAC roles based on team size and "
                 "account type, addressing the 18% of churned accounts that never configured "
                 "role-based access — a feature tightly integrated with Project Atlas."),
            ]},
            {"heading": "3. Expansion Motions", "content": [
                {"bullets": [
                    "Month-2 expansion email: highlights queries saved vs keywords search baseline.",
                    "Usage milestone celebrations: in-app badge at 1 000, 10 000, 100 000 queries.",
                    "QBR programme for Enterprise accounts: quarterly business reviews with CSM.",
                    "Atlas upsell: accounts on Starter with >800 queries/mo get expansion offer.",
                ]},
            ]},
        ],
    }


def prod_10_competitive():
    return {
        "filename": "competitive_analysis_2026.pdf",
        "title":    "Competitive Analysis — Enterprise AI Search 2026",
        "author":   "Suresh Iyer",
        "department": "Product",
        "classification": "internal",
        "date":     "2026-04-02",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This analysis benchmarks NovaTech's Project Atlas against four primary "
                    "competitors: Glean, Guru, Notion AI, and SearchAI (stealth startup). "
                    "NovaTech leads on retrieval accuracy (Qdrant hybrid search) and RBAC "
                    "granularity. Glean leads on breadth of integrations. SearchAI is a "
                    "potential acqui-hire target currently under discussion (see Confidential: "
                    "Acquisition Discussions)."
                )}
            ]},
            {"heading": "1. Competitive Matrix", "content": [
                {"table": (
                    ["Criterion",          "NovaTech Atlas", "Glean",  "Guru",  "Notion AI"],
                    [
                        ["Retrieval accuracy", "★★★★★",      "★★★★",  "★★★",  "★★★"],
                        ["RBAC granularity",   "★★★★★",      "★★★★",  "★★★",  "★★"],
                        ["Integration breadth","★★★",         "★★★★★", "★★★★","★★★★"],
                        ["Self-serve setup",   "★★★",         "★★★★",  "★★★★★","★★★★★"],
                        ["Pricing",            "★★★★",        "★★",    "★★★",  "★★★★"],
                        ["SOC 2 Type II",      "Pending",     "Yes",   "Yes",  "Yes"],
                    ],
                    [2*inch, 1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch]
                )},
            ]},
            {"heading": "2. NovaTech's Differentiation", "content": [
                ("The Qdrant-based hybrid retrieval (dense + BM25 + RRF) gives NovaTech a "
                 "measurable accuracy advantage. In a blind evaluation on the BEIR benchmark, "
                 "Atlas scored 0.74 NDCG@10 vs Glean's published 0.69 and Guru's 0.63. "
                 "Enterprise customers with strict RBAC requirements (financial services, "
                 "healthcare) consistently cite NovaTech's collection-level RBAC as a "
                 "decisive factor."),
            ]},
            {"heading": "3. Emerging Threats", "content": [
                {"bullets": [
                    "SearchAI (stealth): early demos show multimodal retrieval; team is ex-Google.",
                    "Glean v3 (rumoured): reportedly integrating their own vector DB to match our retrieval scores.",
                    "OpenAI enterprise search product: if launched in H2 2026, will commoditise the Starter tier.",
                ]},
            ]},
        ],
    }


# ════════════════════════════════════════════════════════════════════════════════
#  CONFIDENTIAL DOCUMENTS
# ════════════════════════════════════════════════════════════════════════════════

def conf_01_exec_comp():
    return {
        "filename": "executive_compensation_plan_2026.pdf",
        "title":    "Executive Compensation Plan — FY 2026",
        "author":   "Anita Sharma (CHRO)",
        "department": "Confidential",
        "classification": "confidential",
        "date":     "2026-01-15",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This document details the FY 2026 executive compensation framework approved "
                    "by the Compensation Committee on 2026-01-10. Total executive compensation "
                    "includes base salary, annual cash bonus (target 40–80% of base), equity "
                    "refresh (RSUs, 4-year vest), and long-term incentive plan (LTIP) tied to "
                    "ARR growth and Project Atlas adoption milestones."
                )}
            ]},
            {"heading": "1. Executive Compensation Summary", "content": [
                {"table": (
                    ["Role",    "Base Salary", "Target Bonus", "RSU Grant (FY26)", "LTIP Target"],
                    [
                        ["CEO",    "$420 000",  "80% / $336K",  "$1 800 000",   "$600 000"],
                        ["CTO",    "$360 000",  "60% / $216K",  "$1 200 000",   "$400 000"],
                        ["CPO",    "$320 000",  "60% / $192K",  "$1 000 000",   "$350 000"],
                        ["CFO",    "$310 000",  "60% / $186K",  "$900 000",     "$320 000"],
                        ["CHRO",   "$280 000",  "40% / $112K",  "$600 000",     "$200 000"],
                        ["VP Eng", "$290 000",  "50% / $145K",  "$700 000",     "$240 000"],
                        ["VP Sales","$260 000", "80% / $208K",  "$600 000",     "$220 000"],
                    ],
                    [1.3*inch, 1.1*inch, 1.2*inch, 1.4*inch, 1.1*inch]
                )},
            ]},
            {"heading": "2. LTIP Performance Milestones", "content": [
                {"bullets": [
                    "Threshold (50% payout): ARR > $8M by Dec 2026; Project Atlas GA by Sep 2026.",
                    "Target (100% payout): ARR > $12M by Dec 2026; Atlas NPS > 45.",
                    "Stretch (150% payout): ARR > $18M by Dec 2026; Series B closed.",
                ]},
            ]},
            {"heading": "3. Equity Terms", "content": [
                ("All RSU grants vest over 4 years with a 1-year cliff (25% cliff, then monthly "
                 "thereafter). Accelerated vesting (100%) on change of control. Double-trigger "
                 "acceleration applies for involuntary termination within 12 months of a "
                 "qualifying acquisition."),
            ]},
        ],
    }


def conf_02_salary_bands():
    return {
        "filename": "employee_salary_bands_2026.pdf",
        "title":    "Employee Salary Bands — FY 2026 (CONFIDENTIAL)",
        "author":   "Anita Sharma (CHRO)",
        "department": "Confidential",
        "classification": "confidential",
        "date":     "2026-02-01",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This document defines NovaTech's FY 2026 salary bands by role family and "
                    "level. Bands are benchmarked against Radford Global Tech Survey (P50 "
                    "targeting for Levels 1–3, P65 for Levels 4–5) and adjusted for the "
                    "San Francisco Bay Area geo-differential. All offers must fall within the "
                    "defined band; exceptions require VP-level approval."
                )}
            ]},
            {"heading": "1. Engineering Salary Bands", "content": [
                {"table": (
                    ["Level",  "Title",                "Band Min",   "Band Mid",  "Band Max"],
                    [
                        ["E1",   "Junior Engineer",     "$105 000",  "$118 000",  "$130 000"],
                        ["E2",   "Software Engineer",   "$135 000",  "$152 000",  "$168 000"],
                        ["E3",   "Senior Engineer",     "$168 000",  "$192 000",  "$215 000"],
                        ["E4",   "Staff Engineer",      "$215 000",  "$245 000",  "$275 000"],
                        ["E5",   "Principal Engineer",  "$265 000",  "$305 000",  "$345 000"],
                    ],
                    [0.6*inch, 1.8*inch, 1.1*inch, 1.1*inch, 1.1*inch]
                )},
            ]},
            {"heading": "2. Product & Design Bands", "content": [
                {"table": (
                    ["Level",  "Title",             "Band Min",  "Band Mid",  "Band Max"],
                    [
                        ["P1",   "Associate PM",     "$110 000", "$122 000", "$135 000"],
                        ["P2",   "Product Manager",  "$138 000", "$158 000", "$175 000"],
                        ["P3",   "Senior PM",        "$175 000", "$200 000", "$225 000"],
                        ["P4",   "Group PM / Dir",   "$220 000", "$255 000", "$290 000"],
                    ],
                    [0.6*inch, 1.8*inch, 1.1*inch, 1.1*inch, 1.1*inch]
                )},
            ]},
            {"heading": "3. Equity Refresh Eligibility", "content": [
                ("Employees at E3/P3 and above are eligible for annual equity refreshes. "
                 "Refresh grants target 25% of the initial hire grant for Meets Expectations, "
                 "50% for Exceeds, and 100% for Outstanding ratings. FY 2026 refresh budget: "
                 "$4.2M total RSU value across 84 eligible employees."),
            ]},
        ],
    }


def conf_03_acquisition():
    return {
        "filename": "acquisition_discussions_searchai.pdf",
        "title":    "Acquisition Discussions — SearchAI (Project Nightingale)",
        "author":   "CEO / CFO",
        "department": "Confidential",
        "classification": "confidential",
        "date":     "2026-04-12",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "NovaTech is in preliminary discussions to acquire SearchAI, a stealth-stage "
                    "AI search startup (8 employees, ex-Google Brain team). The deal, internally "
                    "codenamed Project Nightingale, would be a talent + technology acquisition "
                    "valued at $18–22M. The primary motivation is the SearchAI team's "
                    "multimodal retrieval capability, which would accelerate Project Atlas's "
                    "roadmap by an estimated 18 months."
                )}
            ]},
            {"heading": "1. Strategic Rationale", "content": [
                ("SearchAI's core IP — a multimodal vector encoder that jointly embeds text, "
                 "tables, and images — directly addresses the most common Feature X limitation "
                 "reported by enterprise beta users: inability to retrieve from embedded charts "
                 "and diagrams in PDF documents."),
                ("The 8-person SearchAI team (4 research engineers, 2 MLEs, 1 PM, 1 infra) "
                 "would be integrated into the Project Atlas engineering org under Deepa Iyer. "
                 "The acquisition is contingent on at least 6 of 8 employees signing retention "
                 "agreements with a 3-year vesting cliff."),
            ]},
            {"heading": "2. Proposed Deal Structure", "content": [
                {"table": (
                    ["Component",       "Value",         "Notes"],
                    [
                        ["Cash at close",  "$8–10M",     "From existing cash reserves"],
                        ["RSU consideration","$10–12M",  "4-year vest, 1-year cliff"],
                        ["Retention pool", "$2M",        "Additional 2-year vest for key engineers"],
                        ["Total",          "$20–24M",    "Subject to due diligence"],
                    ],
                    [1.8*inch, 1.4*inch, 2.8*inch]
                )},
            ]},
            {"heading": "3. Timeline & Risks", "content": [
                {"bullets": [
                    "LOI target: May 2026. Due diligence: 6–8 weeks. Close: Q3 2026.",
                    "Risk 1: Competing offer from Glean (rumoured to be in discussions with SearchAI).",
                    "Risk 2: IP ownership disputes — SearchAI CTO has 2 patents filed at Google; clearance needed.",
                    "Risk 3: Retention risk if acqui-hire terms not competitive with FAANG alternatives.",
                ]},
            ]},
        ],
    }


def conf_04_security_incident():
    return {
        "filename": "security_incident_report_march_2026.pdf",
        "title":    "Security Incident Report — March 2026 (CONFIDENTIAL)",
        "author":   "CISO Office / Security Team",
        "department": "Confidential",
        "classification": "confidential",
        "date":     "2026-03-28",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "On 2026-03-14, NovaTech's Security Operations Centre detected anomalous "
                    "read patterns against the Qdrant production cluster. Investigation confirmed "
                    "that a misconfigured network policy allowed a compromised staging pod to "
                    "reach the production Qdrant API without authentication. An estimated 4 200 "
                    "document chunks were read by the attacker before containment at 03:47 UTC. "
                    "No user PII was accessed. All affected customers (8 enterprise accounts) "
                    "were notified within 72 hours per contractual obligation."
                )}
            ]},
            {"heading": "1. Incident Timeline", "content": [
                {"table": (
                    ["Timestamp (UTC)",  "Event"],
                    [
                        ["2026-03-14 01:22", "First anomalous Qdrant query detected in CloudWatch"],
                        ["2026-03-14 02:15", "SOC analyst escalates to on-call security engineer"],
                        ["2026-03-14 03:47", "Qdrant API key rotated; staging-to-prod network path blocked"],
                        ["2026-03-14 04:30", "Containment confirmed; forensic snapshot taken"],
                        ["2026-03-14 10:00", "CEO and Board notified via encrypted channel"],
                        ["2026-03-16 09:00", "Customer notification emails sent (8 enterprise accounts)"],
                        ["2026-03-28 17:00", "Root cause analysis complete; this report published"],
                    ],
                    [2*inch, 4*inch]
                )},
            ]},
            {"heading": "2. Root Cause", "content": [
                ("A Kubernetes NetworkPolicy update deployed on 2026-03-12 inadvertently "
                 "removed the namespace isolation between <i>staging</i> and <i>retriever</i> "
                 "namespaces. The staging environment had an unpatched container (CVE-2024-8819, "
                 "HIGH severity) that was exploited via a publicly known container escape "
                 "technique. The attacker pivoted to the production Qdrant cluster which, "
                 "at the time, had API key authentication disabled for 'testing purposes' — "
                 "a policy violation by an unnamed engineer."),
            ]},
            {"heading": "3. Remediation & Controls", "content": [
                {"bullets": [
                    "NetworkPolicy restored and locked; changes now require dual approval via PR.",
                    "Qdrant API key authentication re-enabled; key stored in AWS Secrets Manager.",
                    "mTLS enforced between all pods and Qdrant (cert-manager, 90-day rotation).",
                    "Trivy scan added to CI — HIGH/CRITICAL CVEs block all staging deploys.",
                    "SOC 2 Type II scope expanded to include vector database access controls.",
                    "Security awareness training mandated for all engineers by 2026-04-30.",
                ]},
            ]},
            {"heading": "4. Financial & Legal Impact", "content": [
                ("Estimated incident cost: $340 000 (forensics: $80K, legal: $120K, "
                 "customer credits: $140K). Two enterprise accounts requested SLA credits "
                 "totalling $85 000. NovaTech's cyber insurance policy (AIG, $5M limit) "
                 "covers forensics and legal costs; claim filed 2026-03-20."),
            ]},
        ],
    }


def conf_05_audit():
    return {
        "filename": "internal_audit_findings_q1_2026.pdf",
        "title":    "Internal Audit Findings — Q1 2026",
        "author":   "Internal Audit Committee",
        "department": "Confidential",
        "classification": "confidential",
        "date":     "2026-04-14",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "The Internal Audit Committee completed its Q1 2026 review covering "
                    "information security, financial controls, and vendor management. "
                    "Eight findings were identified: 2 High, 4 Medium, 2 Low. The March 2026 "
                    "security incident contributed 3 of the High and Medium findings. "
                    "Remediation deadlines are tracked in the audit management system."
                )}
            ]},
            {"heading": "1. Findings Summary", "content": [
                {"table": (
                    ["ID",   "Finding",                                    "Severity", "Due Date"],
                    [
                        ["A01", "Qdrant API auth disabled in prod (March incident)", "High",   "2026-03-28"],
                        ["A02", "Staging-to-prod network path unrestricted",         "High",   "2026-03-28"],
                        ["A03", "Missing OTel instrumentation on Qdrant client",     "Medium", "2026-04-30"],
                        ["A04", "Vendor NDA expired: SearchAI discussions",          "Medium", "2026-05-01"],
                        ["A05", "Off-cycle expense claims > $5K lacking dual approval","Medium","2026-05-15"],
                        ["A06", "Encryption key rotation overdue (3 keys, >180 days)","Medium","2026-04-30"],
                        ["A07", "Stale IAM roles (12 roles with no activity > 90 days)","Low", "2026-05-31"],
                        ["A08", "Contractor laptop encryption not verified",          "Low",   "2026-06-01"],
                    ],
                    [0.5*inch, 2.8*inch, 0.9*inch, 1.1*inch]
                )},
            ]},
            {"heading": "2. Remediation Status", "content": [
                ("A01 and A02 were remediated on 2026-03-28 as documented in the Security "
                 "Incident Report. A03, A04, and A06 are in progress. A05 has been escalated "
                 "to the CFO for investigation — two expense claims totalling $14 200 lack "
                 "required dual approval documentation."),
            ]},
        ],
    }


def conf_06_budget():
    return {
        "filename": "budget_forecast_2027.pdf",
        "title":    "Budget Forecast — FY 2027 (Draft)",
        "author":   "CFO / Finance Team",
        "department": "Confidential",
        "classification": "confidential",
        "date":     "2026-04-20",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This draft FY 2027 budget forecast models three scenarios (Base, Upside, "
                    "Downside) based on Project Atlas GA adoption rates. The Base scenario "
                    "projects $22M ARR by Dec 2027, requiring a $14M Series B raise in Q4 2026 "
                    "to fund the planned headcount expansion from 62 to 110 employees. The "
                    "Project Nightingale acquisition ($20–24M) is included as a contingent item "
                    "in the Upside scenario only."
                )}
            ]},
            {"heading": "1. Revenue Forecast", "content": [
                {"table": (
                    ["Scenario",   "FY27 ARR",  "Atlas % of ARR", "Series B Required"],
                    [
                        ["Downside",   "$14M",  "45%",            "$8M"],
                        ["Base",       "$22M",  "62%",            "$14M"],
                        ["Upside",     "$34M",  "78%",            "$20M"],
                    ],
                    [1.5*inch, 1.2*inch, 1.8*inch, 1.8*inch]
                )},
            ]},
            {"heading": "2. Headcount & Cost Plan (Base)", "content": [
                {"table": (
                    ["Department",     "FY26 HC",  "FY27 HC",  "Net Adds", "Cost ($M)"],
                    [
                        ["Engineering", "28",       "46",       "+18",      "$11.2"],
                        ["Product",     "8",        "12",       "+4",       "$2.8"],
                        ["Sales & CS",  "14",       "28",       "+14",      "$6.4"],
                        ["G&A",         "12",       "16",       "+4",       "$4.2"],
                        ["Total",       "62",       "102",      "+40",      "$24.6"],
                    ],
                    [1.6*inch, 1*inch, 1*inch, 1*inch, 1.2*inch]
                )},
            ]},
            {"heading": "3. Project Atlas Budget Allocation", "content": [
                ("Project Atlas is the primary investment vehicle in FY 2027. Allocated "
                 "budget: $8.4M (engineering compute, GPU inference, Qdrant cluster expansion, "
                 "and LLM API costs). This represents 34% of total opex budget. The Project "
                 "Atlas budget was $2.4M in FY 2026 (see Board Meeting Minutes for the "
                 "approved figure)."),
            ]},
        ],
    }


def conf_07_board_minutes():
    return {
        "filename": "board_meeting_minutes_q1_2026.pdf",
        "title":    "Board Meeting Minutes — Q1 2026 (CONFIDENTIAL)",
        "author":   "Board Secretary",
        "department": "Confidential",
        "classification": "confidential",
        "date":     "2026-03-31",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "Minutes of the NovaTech Board of Directors meeting held 2026-03-30 via "
                    "Zoom. Attendees: 5 board members, CEO, CFO, CTO, General Counsel. "
                    "Key resolutions: (1) approved Project Atlas budget of $2.8M for FY 2026 "
                    "(amended from the originally proposed $2.4M following the March security "
                    "incident remediation costs); (2) authorised preliminary due diligence on "
                    "Project Nightingale (SearchAI acquisition); (3) approved Series B mandate "
                    "to Goldman Sachs."
                )}
            ]},
            {"heading": "1. CEO Quarterly Update", "content": [
                ("ARR reached $9.2M as of March 2026, up 28% QoQ. Project Atlas private beta "
                 "has 34 enterprise users; NPS of 44. The March 2026 security incident was "
                 "disclosed in detail; the Board expressed concern about the timeline to SOC 2 "
                 "Type II certification and its impact on enterprise sales. The CISO presented "
                 "the remediation roadmap; the Board approved additional $400K security budget."),
            ]},
            {"heading": "2. Project Atlas Budget Resolution", "content": [
                ("Resolution 2026-Q1-01: The Board approves a revised Project Atlas FY 2026 "
                 "budget of $2.8M, amended from the $2.4M approved at the December 2025 "
                 "board meeting. The additional $400K covers March 2026 security incident "
                 "remediation, SOC 2 audit fees, and additional GPU capacity for the reranker "
                 "service. Vote: 5 in favour, 0 opposed, 0 abstain."),
                ("Note: The Budget Forecast 2027 document incorrectly references the Project "
                 "Atlas FY 2026 budget as $2.4M; the correct approved figure is $2.8M per "
                 "this resolution."),
            ]},
            {"heading": "3. Series B Mandate", "content": [
                ("The Board authorised management to engage Goldman Sachs as lead advisor "
                 "for a Series B fundraise of $14–20M, targeting close in Q4 2026. The "
                 "Series B will fund the FY 2027 headcount plan and Project Nightingale "
                 "acquisition if due diligence is satisfactory."),
            ]},
        ],
    }


def conf_08_infra_risk():
    return {
        "filename": "infrastructure_risk_assessment_2026.pdf",
        "title":    "Infrastructure Risk Assessment — 2026 (CONFIDENTIAL)",
        "author":   "VP Engineering / CISO",
        "department": "Confidential",
        "classification": "confidential",
        "date":     "2026-04-10",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This risk assessment evaluates NovaTech's infrastructure risks as of Q2 2026. "
                    "Top risks: (1) single-region EKS dependency — DR cluster in eu-west-1 is "
                    "not yet at parity; (2) Qdrant cluster at 78% capacity — needs expansion "
                    "before Q3 peak; (3) LLM vendor concentration (100% Anthropic) — "
                    "no fallback model configured. Post-March 2026 incident, the security "
                    "posture has improved but 3 audit findings remain open."
                )}
            ]},
            {"heading": "1. Risk Register", "content": [
                {"table": (
                    ["ID", "Risk",                              "Likelihood", "Impact", "Rating"],
                    [
                        ["R01","Single-region EKS — DR at 60% parity", "Medium", "Critical","High"],
                        ["R02","Qdrant at 78% capacity",               "High",   "High",    "High"],
                        ["R03","LLM vendor concentration (Anthropic)",  "Low",    "Critical","Medium"],
                        ["R04","3 open audit findings (A03/A06/A07)",  "Medium", "Medium",  "Medium"],
                        ["R05","AWS cost overrun — GPU instances",     "High",   "Medium",  "Medium"],
                        ["R06","Key-person dependency: Deepa Iyer",    "Low",    "High",    "Medium"],
                    ],
                    [0.5*inch, 2.6*inch, 1*inch, 1*inch, 0.8*inch]
                )},
            ]},
            {"heading": "2. Qdrant Capacity Risk", "content": [
                ("The production Qdrant cluster is projected to reach 90% capacity by "
                 "2026-07-01 based on current ingestion rates (120 000 new chunks/week). "
                 "At 90% utilisation, HNSW search performance degrades by approximately "
                 "40% due to increased disk I/O. A 3-node cluster expansion (r6g.2xlarge) "
                 "is budgeted at $4 200/month and has been approved in the Q3 engineering "
                 "budget. Target expansion date: 2026-06-15."),
            ]},
            {"heading": "3. LLM Vendor Concentration", "content": [
                ("NovaTech currently routes 100% of Project Atlas LLM inference through "
                 "the Anthropic API (Claude claude-sonnet-4-6). An Anthropic outage would "
                 "cause complete Project Atlas service unavailability. Mitigation: integrate "
                 "a secondary LLM provider (OpenAI or AWS Bedrock) with automatic failover "
                 "via LiteLLM router. Target: Q3 2026."),
            ]},
        ],
    }


def conf_09_compliance():
    return {
        "filename": "compliance_investigation_vendor_2026.pdf",
        "title":    "Compliance Investigation — Vendor Expense Irregularities 2026",
        "author":   "General Counsel / CFO",
        "department": "Confidential",
        "classification": "confidential",
        "date":     "2026-04-22",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "This document summarises the findings of an internal compliance "
                    "investigation into vendor expense irregularities flagged during the Q1 "
                    "2026 internal audit (Finding A05). Two purchase orders totalling $14 200 "
                    "lacked required dual-approval documentation. Investigation confirms the "
                    "expenses were legitimate business purchases but processed in violation of "
                    "the company's procurement policy. No fraud or misappropriation found."
                )}
            ]},
            {"heading": "1. Scope & Findings", "content": [
                ("The investigation covered 847 vendor transactions from January–March 2026. "
                 "Two transactions were flagged: (a) $8 400 software license (Weights & Biases "
                 "Teams) approved by a single approver; (b) $5 800 cloud GPU credits "
                 "(Lambda Labs) charged to a personal card and expensed without prior PO. "
                 "Both purchases are directly attributable to Project Atlas development."),
            ]},
            {"heading": "2. Policy Violations", "content": [
                {"bullets": [
                    "Procurement Policy §4.2: purchases > $5 000 require dual approval (manager + Finance).",
                    "Expense Policy §7.1: pre-approval required for all software SaaS > $1 000/year.",
                    "Expense Policy §7.3: personal card charges > $2 000 require CFO sign-off.",
                ]},
            ]},
            {"heading": "3. Remediation", "content": [
                ("Retroactive dual approvals have been obtained for both transactions. "
                 "The purchasing engineer has completed a mandatory procurement policy "
                 "refresher. Finance is implementing an automated procurement gate in "
                 "the expense management system (Ramp) to enforce dual-approval at point "
                 "of purchase for all transactions > $3 000. Deployment target: 2026-05-15."),
            ]},
        ],
    }


def conf_10_partnership():
    return {
        "filename": "strategic_partnership_negotiations_2026.pdf",
        "title":    "Strategic Partnership Negotiations — FinCorp & RetailMax 2026",
        "author":   "VP Business Development",
        "department": "Confidential",
        "classification": "confidential",
        "date":     "2026-04-08",
        "sections": [
            {"heading": None, "content": [
                {"exec_summary": (
                    "NovaTech is in active partnership negotiations with two strategic accounts: "
                    "FinCorp (financial services, 12 000 employees) and RetailMax (e-commerce, "
                    "4 500 employees). Combined, these deals represent $2.1M ARR and will "
                    "serve as anchor case studies for the Project Atlas enterprise segment. "
                    "Both deals are gated on SOC 2 Type II certification and EU data residency "
                    "completion."
                )}
            ]},
            {"heading": "1. FinCorp Deal Summary", "content": [
                ("FinCorp is deploying Project Atlas across their compliance and regulatory "
                 "documentation workflow — 2.4M documents, 18 000 active Confluence pages. "
                 "Proposed ARR: $480 000/year (3-year commitment). Key requirements: "
                 "on-premise Qdrant deployment option, FIPS 140-2 encryption, and a dedicated "
                 "Customer Success manager."),
                ("Deal risk: FinCorp's procurement team requires SOC 2 Type II before contract "
                 "signature. If NovaTech's SOC 2 audit (scheduled Q3 2026) slips, FinCorp has "
                 "indicated they will proceed with a competitor. This creates a hard dependency "
                 "between the SOC 2 timeline and the FinCorp close."),
            ]},
            {"heading": "2. RetailMax Deal Summary", "content": [
                {"table": (
                    ["Item",              "Detail"],
                    [
                        ["Proposed ARR",   "$180 000/year"],
                        ["Contract Term",  "2 years"],
                        ["Use Case",       "Product knowledge base Q&A for 800 support agents"],
                        ["Queries/mo",     "~400 000"],
                        ["Key Requirement","EU data residency (GDPR compliance)"],
                        ["Close Target",   "2026-08-01"],
                    ],
                    [2*inch, 4*inch]
                )},
            ]},
            {"heading": "3. Negotiation Status", "content": [
                {"bullets": [
                    "FinCorp: Term sheet signed 2026-03-05; technical due diligence ongoing.",
                    "RetailMax: MSA under legal review; data processing agreement (DPA) in draft.",
                    "Both deals: pricing finalised; SLA terms (99.9% uptime, <500ms P95) under negotiation.",
                    "Risk: Project Atlas GA slip beyond August 2026 may cause RetailMax to push close to Q4.",
                ]},
            ]},
        ],
    }


# ════════════════════════════════════════════════════════════════════════════════
#  CORPUS BUILDER
# ════════════════════════════════════════════════════════════════════════════════

# Map document functions to their output directories
DOCUMENT_REGISTRY = [
    # (generator_fn, output_dir)
    (eng_01_fastapi_architecture, ENG_DIR),
    (eng_02_qdrant_deployment,    ENG_DIR),
    (eng_03_redis_caching,        ENG_DIR),
    (eng_04_celery_jobs,          ENG_DIR),
    (eng_05_api_versioning,       ENG_DIR),
    (eng_06_observability,        ENG_DIR),
    (eng_07_kubernetes,           ENG_DIR),
    (eng_08_cicd,                 ENG_DIR),
    (eng_09_vector_search,        ENG_DIR),
    (eng_10_rag_architecture,     ENG_DIR),
    (prod_01_roadmap,             PROD_DIR),
    (prod_02_pricing,             PROD_DIR),
    (prod_03_customer_feedback,   PROD_DIR),
    (prod_04_feature_prioritization, PROD_DIR),
    (prod_05_analytics,           PROD_DIR),
    (prod_06_market_research,     PROD_DIR),
    (prod_07_segmentation,        PROD_DIR),
    (prod_08_launch_plan,         PROD_DIR),
    (prod_09_retention,           PROD_DIR),
    (prod_10_competitive,         PROD_DIR),
    (conf_01_exec_comp,           CONF_DIR),
    (conf_02_salary_bands,        CONF_DIR),
    (conf_03_acquisition,         CONF_DIR),
    (conf_04_security_incident,   CONF_DIR),
    (conf_05_audit,               CONF_DIR),
    (conf_06_budget,              CONF_DIR),
    (conf_07_board_minutes,       CONF_DIR),
    (conf_08_infra_risk,          CONF_DIR),
    (conf_09_compliance,          CONF_DIR),
    (conf_10_partnership,         CONF_DIR),
]


def generate_corpus():
    """Generate all 30 PDFs and write metadata.csv."""
    os.makedirs(ENG_DIR, exist_ok=True)
    os.makedirs(PROD_DIR, exist_ok=True)
    os.makedirs(CONF_DIR, exist_ok=True)

    metadata_rows = []

    print("\n🔨  Generating NovaTech enterprise knowledge base...\n")

    for gen_fn, output_dir in DOCUMENT_REGISTRY:
        spec = gen_fn()
        filepath = os.path.join(output_dir, spec["filename"])
        write_pdf(filepath, {
            "title":          spec["title"],
            "author":         spec["author"],
            "department":     spec["department"],
            "classification": spec["classification"],
            "date":           spec["date"],
        }, spec["sections"])

        metadata_rows.append({
            "document_name":  spec["filename"],
            "department":     spec["department"],
            "classification": spec["classification"],
            "author":         spec["author"],
            "created_date":   spec["date"],
        })

    # Write metadata CSV
    with open(METADATA_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "document_name", "department", "classification",
            "author", "created_date"
        ])
        writer.writeheader()
        writer.writerows(metadata_rows)

    print(f"\n✅  {len(DOCUMENT_REGISTRY)} PDFs generated.")
    print(f"📄  Metadata written → {os.path.relpath(METADATA_PATH, BASE_DIR)}")
    print(f"\n📁  Corpus root: {BASE_DIR}\n")


if __name__ == "__main__":
    generate_corpus()
