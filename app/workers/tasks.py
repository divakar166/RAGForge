"""Celery tasks for async document processing — sync Supabase + Qdrant Cloud inference + BM25 sparse."""

import logging
import os
import uuid
from typing import Any

from qdrant_client import models as qmodels
from qdrant_client.http.models import Document as QdrantDocument

from app.core.config import settings
from app.db.supabase import get_sync_supabase
from app.rag.chunking.pipeline import ChunkingPipeline
from app.rag.parser import parse_document
from app.rag.sparse import BM25SparseEncoder
from app.rag.vector_store import QdrantStore, allowed_roles_for_classification
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_sparse_encoder(texts: list[str]) -> BM25SparseEncoder:
    encoder = BM25SparseEncoder()
    encoder.fit(texts)
    return encoder


@celery_app.task(name="process_document", bind=True, max_retries=3, default_retry_delay=30, acks_late=True)
def process_document(self, document_id: str, organization_id: str = "") -> dict[str, Any]:
    logger.info("Processing document %s for org %s", document_id, organization_id)

    supabase = get_sync_supabase()

    try:
        doc_resp = supabase.table("documents").select("*").eq("id", document_id).single().execute()
        doc = doc_resp.data
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        supabase.table("documents").update({"status": "processing"}).eq("id", document_id).execute()

        file_path = doc["file_path"]
        if not os.path.isabs(file_path):
            if file_path.startswith("./"):
                file_path = os.path.abspath(file_path)
            else:
                file_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, file_path))
        text = parse_document(file_path)
        logger.info("Parsed document %s: %d chars", document_id, len(text))

        if not text.strip():
            supabase.table("documents").update({"status": "failed"}).eq("id", document_id).execute()
            return {"document_id": document_id, "status": "failed", "error": "Empty document"}

        pipeline = ChunkingPipeline()
        chunk_strategy = pipeline.STRATEGY_MAP.get(doc["file_type"], "recursive")
        chunks = pipeline.chunk(text, doc["title"] or doc["file_path"], doc["file_type"], chunk_strategy)
        logger.info("Chunked into %d chunks", len(chunks))

        # Build points — dense always via Qdrant Cloud inference
        points: list[qmodels.PointStruct] = []
        sparse_encoder = None
        if not settings.QDRANT_CLOUD_INFERENCE:
            sparse_encoder = _get_sparse_encoder([c.content for c in chunks])

        for i, chunk in enumerate(chunks):
            classification = doc.get("classification", "internal")
            payload = {
                "document_id": document_id,
                "chunk_index": chunk.index,
                "doc_title": doc["title"],
                "section_path": chunk.section_path or "",
                "strategy": chunk.strategy,
                "content": chunk.content,
                "uploaded_by_id": doc["uploaded_by_id"],
                "classification": classification,
                "allowed_roles": doc.get("allowed_roles") or allowed_roles_for_classification(classification),
                "collection_id": doc.get("collection_id") or "",
            }

            vector: dict[str, Any] = {
                "dense": QdrantDocument(
                    text=chunk.content,
                    model=settings.EMBEDDING_MODEL,
                ),
            }

            if settings.QDRANT_CLOUD_INFERENCE:
                vector["sparse"] = QdrantDocument(
                    text=chunk.content,
                    model=settings.SPARSE_MODEL,
                )
            else:
                sparse_indices, sparse_values = sparse_encoder.encode(chunk.content)
                vector["sparse"] = qmodels.SparseVector(
                    indices=sparse_indices,
                    values=sparse_values,
                )

            point = qmodels.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}:{chunk.index}")),
                vector=vector,
                payload=payload,
            )
            points.append(point)

        effective_org_id = organization_id or doc["organization_id"]
        store = QdrantStore(organization_id=effective_org_id)
        store.ensure_collection(settings.EMBEDDING_DIM)
        store.upsert_chunks(points)

        supabase.table("documents").update({
            "status": "indexed",
            "chunk_count": len(points),
        }).eq("id", document_id).execute()

        logger.info("Document %s indexed successfully (%d chunks)", document_id, len(points))
        return {"document_id": document_id, "status": "indexed", "chunks": len(points)}

    except Exception as exc:
        logger.exception("Failed to process document %s", document_id)
        try:
            supabase.table("documents").update({"status": "failed"}).eq("id", document_id).execute()
        except Exception:
            pass
        raise self.retry(exc=exc) from exc