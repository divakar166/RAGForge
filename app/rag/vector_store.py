"""Qdrant vector store wrapper with per-organization collections."""

import logging
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client import models as qmodels

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantStore:
    """Per-organization Qdrant store.

    Each organization gets its own collection named ``org_{organization_id}``,
    providing tenant isolation at the vector database level.
    """

    def __init__(
        self,
        organization_id: str = "",
        host: str = "",
        port: int = 0,
        api_key: str | None = None,
        vector_size: int = 384,
    ):
        self.host = host or settings.QDRANT_HOST
        self.port = port or settings.QDRANT_PORT
        self.api_key = api_key or settings.QDRANT_API_KEY
        self.organization_id = organization_id
        self.collection = f"org_{organization_id}" if organization_id else settings.QDRANT_COLLECTION
        self._client: QdrantClient | None = None
        self._ensured = False
        self._vector_size = vector_size

    def _ensure(self) -> None:
        if not self._ensured:
            self.ensure_collection(vector_size=self._vector_size)
            self._ensured = True

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                host=self.host,
                port=self.port,
                api_key=self.api_key,
                prefer_grpc=False,
            )
        return self._client

    def ensure_collection(self, vector_size: int = 384) -> None:
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config={
                    "dense": qmodels.VectorParams(
                        size=vector_size,
                        distance=qmodels.Distance.COSINE,
                    ),
                },
                sparse_vectors_config={
                    "sparse": qmodels.SparseVectorParams(
                        modifier=qmodels.Modifier.IDF,
                    ),
                },
            )
            logger.info("Created Qdrant collection '%s'", self.collection)

            for field_name in ("document_id", "uploaded_by_id", "is_public_in_org", "collection_id"):
                    self.client.create_payload_index(
                        collection_name=self.collection,
                        field_name=field_name,
                        field_schema=qmodels.PayloadSchemaType.KEYWORD
                        if field_name != "is_public_in_org"
                        else qmodels.PayloadSchemaType.BOOL,
                    )

    def upsert_chunks(self, points: list[qmodels.PointStruct]) -> None:
        self._ensure()
        self.client.upsert(
            collection_name=self.collection,
            points=points,
            wait=True,
        )

    def hybrid_search(
        self,
        query_dense: list[float],
        query_sparse: tuple[list[int], list[float]] | None,
        rbac_filter: Optional[qmodels.Filter] = None,
        top_k: int = 20,
        prefetch_limit: int = 50,
    ) -> list[qmodels.ScoredPoint]:
        self._ensure()
        prefetches = [
            qmodels.Prefetch(
                query=query_dense,
                using="dense",
                limit=prefetch_limit,
                filter=rbac_filter,
            ),
        ]

        if query_sparse and query_sparse[0]:
            indices, values = query_sparse
            prefetches.append(
                qmodels.Prefetch(
                    query=qmodels.SparseVector(indices=indices, values=values),
                    using="sparse",
                    limit=prefetch_limit,
                    filter=rbac_filter,
                ),
            )

        result = self.client.query_points(
            collection_name=self.collection,
            prefetch=prefetches,
            query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )
        return result.points

    def search_dense(
        self,
        query: list[float],
        rbac_filter: Optional[qmodels.Filter] = None,
        top_k: int = 20,
    ) -> list[qmodels.ScoredPoint]:
        self._ensure()
        result = self.client.query_points(
            collection_name=self.collection,
            query=query,
            using="dense",
            query_filter=rbac_filter,
            limit=top_k,
            with_payload=True,
        )
        return result.points

    def delete_by_document_id(self, document_id: str) -> None:
        self._ensure()
        self.client.delete(
            collection_name=self.collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id),
                        ),
                    ],
                ),
            ),
        )

    def build_rbac_filter(self, user_id: str, org_role: str) -> qmodels.Filter | None:
        """Build Qdrant filter for org-scoped RBAC.

        Admins/owners see everything. Others see public docs + own uploaded docs.
        """
        if org_role in ("owner", "admin"):
            return None

        return qmodels.Filter(
            min_should=qmodels.MinShould(
                conditions=[
                    qmodels.FieldCondition(
                        key="is_public_in_org",
                        match=qmodels.MatchValue(value=True),
                    ),
                    qmodels.FieldCondition(
                        key="uploaded_by_id",
                        match=qmodels.MatchValue(value=user_id),
                    ),
                ],
                min_count=1,
            ),
        )

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
