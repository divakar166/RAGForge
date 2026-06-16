"""Celery tasks for async document processing."""

import logging
import uuid
from typing import Any

import httpx
from qdrant_client import models as qmodels
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.rag.chunking.pipeline import ChunkingPipeline
from app.rag.parser import parse_document
from app.rag.sparse import BM25SparseEncoder
from app.rag.vector_store import QdrantStore
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_engine = None
_SessionFactory = None


def _get_db():
    global _engine, _SessionFactory
    if _engine is None:
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
        _engine = create_engine(sync_url, pool_pre_ping=True)
        _SessionFactory = sessionmaker(bind=_engine)
    return _SessionFactory()


def _get_tei_embedding(texts: list[str]) -> list[list[float]]:
    endpoint = settings.TEI_ENDPOINT.rstrip("/")
    with httpx.Client(timeout=120) as client:
        resp = client.post(
            f"{endpoint}/embed",
            json={"inputs": texts},
        )
        resp.raise_for_status()
        data = resp.json()
    return data if isinstance(data, list) else data.get("data", [])


def _get_sparse_encoder(texts: list[str]) -> BM25SparseEncoder:
    encoder = BM25SparseEncoder()
    encoder.fit(texts)
    return encoder


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, acks_late=True)
def process_document(self, document_id: str, organization_id: str = "") -> dict[str, Any]:
    """Parse, chunk, embed, and index a document into the org-scoped Qdrant collection."""
    logger.info("Processing document %s for org %s", document_id, organization_id)

    db = _get_db()

    try:
        from app.db.models.document import Document

        doc = db.execute(select(Document).where(Document.id == uuid.UUID(document_id))).scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        doc.status = "processing"
        db.commit()

        text = parse_document(doc.file_path)
        logger.info("Parsed document %s: %d chars", document_id, len(text))

        if not text.strip():
            doc.status = "failed"
            db.commit()
            return {"document_id": document_id, "status": "failed", "error": "Empty document"}

        pipeline = ChunkingPipeline()
        chunk_strategy = pipeline.STRATEGY_MAP.get(doc.file_type, "recursive")
        chunks = pipeline.chunk(text, doc.title or doc.file_path, doc.file_type, chunk_strategy)
        logger.info("Chunked into %d chunks", len(chunks))

        chunk_texts = [c.content for c in chunks]
        batch_size = 32
        all_embeddings: list[list[float]] = []

        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i : i + batch_size]
            embeddings = _get_tei_embedding(batch)
            all_embeddings.extend(embeddings)

        sparse_encoder = _get_sparse_encoder(chunk_texts)
        all_sparse: list[tuple[list[int], list[float]]] = [sparse_encoder.encode(t) for t in chunk_texts]

        # Build points with deterministic IDs
        points: list[qmodels.PointStruct] = []
        for i, chunk in enumerate(chunks):
            payload = {
                "document_id": document_id,
                "chunk_index": chunk.index,
                "doc_title": doc.title,
                "section_path": chunk.section_path or "",
                "strategy": chunk.strategy,
                "content": chunk.content,
                "uploaded_by_id": str(doc.uploaded_by_id),
                "is_public_in_org": doc.is_public_in_org,
                "collection_id": str(doc.collection_id) if doc.collection_id else "",
            }

            sparse_indices, sparse_values = all_sparse[i]

            point = qmodels.PointStruct(
                id=f"{document_id}:{chunk.index}",
                vector={
                    "dense": all_embeddings[i] if i < len(all_embeddings) else [],
                    "sparse": qmodels.SparseVector(
                        indices=sparse_indices,
                        values=sparse_values,
                    ),
                },
                payload=payload,
            )
            points.append(point)

        # Use org-scoped collection
        effective_org_id = organization_id or str(doc.organization_id)
        store = QdrantStore(organization_id=effective_org_id)
        store.ensure_collection(len(all_embeddings[0]) if all_embeddings else settings.EMBEDDING_DIM)
        store.upsert_chunks(points)

        doc.status = "indexed"
        doc.chunk_count = len(points)
        db.commit()

        logger.info("Document %s indexed successfully (%d chunks)", document_id, len(points))
        return {"document_id": document_id, "status": "indexed", "chunks": len(points)}

    except Exception as exc:
        logger.exception("Failed to process document %s", document_id)
        try:
            db.execute(update(Document).where(Document.id == uuid.UUID(document_id)).values(status="failed"))
            db.commit()
        except Exception:
            pass
        raise self.retry(exc=exc) from exc

    finally:
        db.close()
