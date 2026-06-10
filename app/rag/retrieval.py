"""Retrieval orchestrator — hybrid search + reranking + RBAC filtering."""

import logging
from dataclasses import dataclass, field

from app.core.config import settings
from app.monitoring.tracing import observe
from app.rag.embeddings import TEIEmbeddingProvider
from app.rag.reranker import Reranker
from app.rag.sparse import BM25SparseEncoder
from app.rag.vector_store import QdrantStore

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    content: str
    score: float
    document_id: str
    doc_title: str
    chunk_index: int
    section_path: str | None = None
    metadata: dict = field(default_factory=dict)


class RetrievalPipeline:
    """Full retrieval pipeline: embed → hybrid search → rerank."""

    def __init__(
        self,
        embed_provider: TEIEmbeddingProvider | None = None,
        sparse_encoder: BM25SparseEncoder | None = None,
        vector_store: QdrantStore | None = None,
        reranker: Reranker | None = None,
    ):
        self.embed_provider = embed_provider or TEIEmbeddingProvider()
        self.sparse_encoder = sparse_encoder or BM25SparseEncoder()
        self.vector_store = vector_store or QdrantStore()
        self.reranker = reranker or Reranker()

    @observe(name="retrieval_pipeline_search")
    async def search(
        self,
        query: str,
        user_id: str,
        role_ids: list[str],
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        # 1. Get dense query embedding
        dense_result = await self.embed_provider.embed([query])
        query_dense = dense_result["embeddings"][0]

        # 2. Get sparse query representation
        if self.sparse_encoder.is_fitted:
            query_sparse = self.sparse_encoder.encode(query)
        else:
            query_sparse = ([], [])

        # 3. Build RBAC filter
        rbac_filter = self.vector_store.build_rbac_filter(user_id, role_ids)

        # 4. Hybrid search
        prefetch_limit = max(top_k * 4, settings.TOP_K_RETRIEVAL)
        raw_results = self.vector_store.hybrid_search(
            query_dense=query_dense,
            query_sparse=query_sparse if any(query_sparse[0]) else None,
            rbac_filter=rbac_filter,
            top_k=prefetch_limit if settings.RERANKER_ENABLED else top_k,
            prefetch_limit=prefetch_limit,
        )

        if not raw_results:
            return []

        # 5. Rerank with cross-encoder
        if settings.RERANKER_ENABLED and len(raw_results) > top_k:
            texts = [r.payload.get("content", "") for r in raw_results if r.payload]
            reranked = await self.reranker.rerank(query, texts)

            # Map back to original results using content matching
            text_to_result = {r.payload.get("content", ""): r for r in raw_results if r.payload}
            reranked_results: list[RetrievalResult] = []
            for text, score in reranked[:top_k]:
                original = text_to_result.get(text)
                if original and original.payload:
                    reranked_results.append(
                        RetrievalResult(
                            content=text,
                            score=score,
                            document_id=original.payload.get("document_id", ""),
                            doc_title=original.payload.get("doc_title", ""),
                            chunk_index=original.payload.get("chunk_index", 0),
                            section_path=original.payload.get("section_path"),
                            metadata=dict(original.payload),
                        )
                    )
            return reranked_results

        # Skip rerank — just return top_k
        results: list[RetrievalResult] = []
        for r in raw_results[:top_k]:
            if r.payload:
                results.append(
                    RetrievalResult(
                        content=r.payload.get("content", ""),
                        score=r.score,
                        document_id=r.payload.get("document_id", ""),
                        doc_title=r.payload.get("doc_title", ""),
                        chunk_index=r.payload.get("chunk_index", 0),
                        section_path=r.payload.get("section_path"),
                        metadata=dict(r.payload),
                    )
                )
        return results
