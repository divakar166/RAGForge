"""Qdrant vector store wrapper with hybrid search support."""

import logging
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client import models as qmodels

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantStore:
    """Wraps Qdrant client for dense + sparse hybrid search with RBAC."""

    def __init__(
        self,
        host: str = "",
        port: int = 0,
        api_key: str | None = None,
        collection: str = "",
    ):
        self.host = host or settings.QDRANT_HOST
        self.port = port or settings.QDRANT_PORT
        self.api_key = api_key or settings.QDRANT_API_KEY
        self.collection = collection or settings.QDRANT_COLLECTION
        self._client: QdrantClient | None = None

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

            # Create payload indexes for RBAC filtering
            self.client.create_payload_index(
                collection_name=self.collection,
                field_name="document_id",
                field_type=qmodels.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.collection,
                field_name="owner_id",
                field_type=qmodels.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.collection,
                field_name="is_public",
                field_type=qmodels.PayloadSchemaType.BOOL,
            )

    def upsert_chunks(
        self,
        points: list[qmodels.PointStruct],
    ) -> None:
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

    def build_rbac_filter(
        self,
        user_id: str,
        role_ids: list[str],
    ) -> qmodels.Filter:
        """Build Qdrant filter for RBAC: user can see public docs + own docs + role-accessible docs."""
        should_conditions: list[qmodels.Condition] = [
            qmodels.FieldCondition(
                key="is_public",
                match=qmodels.MatchValue(value=True),
            ),
            qmodels.FieldCondition(
                key="owner_id",
                match=qmodels.MatchValue(value=user_id),
            ),
        ]

        if role_ids:
            should_conditions.append(
                qmodels.FieldCondition(
                    key="allowed_role_ids",
                    match=qmodels.MatchAny(any=role_ids),
                ),
            )

        return qmodels.Filter(
            min_should=qmodels.MinShould(conditions=should_conditions, min_count=1),
        )

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
