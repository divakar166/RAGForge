"""Qdrant Cloud vector store wrapper with per-organization collections."""

import logging
from typing import Optional, Union

from qdrant_client import QdrantClient
from qdrant_client import models as qmodels
from qdrant_client.http.models import Document as QdrantDocument

from app.core.config import settings

logger = logging.getLogger(__name__)

CLASSIFICATION_ROLE_MAP: dict[str, list[str]] = {
    "public": ["viewer", "member", "admin", "owner"],
    "internal": ["member", "admin", "owner"],
    "confidential": ["admin", "owner"],
}


def allowed_roles_for_classification(classification: str) -> list[str]:
    return CLASSIFICATION_ROLE_MAP.get(classification, ["member", "admin", "owner"])


class QdrantStore:
    """Per-organization Qdrant store, backed by Qdrant Cloud.

    Each organization gets its own collection named ``org_{organization_id}``,
    providing tenant isolation at the vector database level.
    """

    def __init__(
        self,
        organization_id: str = "",
        url: str = "",
        api_key: str | None = None,
        vector_size: int = 384,
    ):
        self.url = url or settings.QDRANT_URL
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
                url=self.url,
                api_key=self.api_key,
                cloud_inference=settings.QDRANT_CLOUD_INFERENCE,
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

            for field_name in ("document_id", "uploaded_by_id", "allowed_roles", "collection_id", "classification"):
                self.client.create_payload_index(
                    collection_name=self.collection,
                    field_name=field_name,
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )

    def upsert_chunks(self, points: list[qmodels.PointStruct]) -> None:
        self._ensure()
        self.client.upsert(
            collection_name=self.collection,
            points=points,
            wait=True,
        )

    def _resolve_dense_query(self, query_dense: Union[str, list[float]]) -> Union[str, list[float], QdrantDocument]:
        if settings.QDRANT_CLOUD_INFERENCE and isinstance(query_dense, str):
            return QdrantDocument(text=query_dense, model=settings.EMBEDDING_MODEL)
        return query_dense

    def hybrid_search(
        self,
        query_dense: Union[str, list[float]],
        query_sparse: tuple[list[int], list[float]] | None,
        rbac_filter: Optional[qmodels.Filter] = None,
        top_k: int = 20,
        prefetch_limit: int = 50,
    ) -> list[qmodels.ScoredPoint]:
        self._ensure()
        dense_query = self._resolve_dense_query(query_dense)
        prefetches = [
            qmodels.Prefetch(
                query=dense_query,
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
        query: Union[str, list[float]],
        rbac_filter: Optional[qmodels.Filter] = None,
        top_k: int = 20,
    ) -> list[qmodels.ScoredPoint]:
        self._ensure()
        dense_query = self._resolve_dense_query(query)
        result = self.client.query_points(
            collection_name=self.collection,
            query=dense_query,
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
        if org_role in ("owner", "admin"):
            return None

        return qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="allowed_roles",
                    match=qmodels.MatchValue(value=org_role),
                ),
            ],
        )

    def update_point_payload(self, document_id: str, payload: dict) -> None:
        self._ensure()
        self.client.set_payload(
            collection_name=self.collection,
            payload=payload,
            points=qmodels.FilterSelector(
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

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None