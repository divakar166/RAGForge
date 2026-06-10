"""Cross-encoder reranking via TEI or local model."""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranking.

    Primary: TEI /rerank endpoint.
    Fallback: local sentence-transformers cross-encoder.
    """

    def __init__(
        self,
        endpoint: str = "",
        use_local: bool = False,
        model: str = "",
    ):
        self.endpoint = (endpoint or settings.TEI_ENDPOINT).rstrip("/")
        self.use_local = use_local
        self.model = (
            model or settings.RERANKER_MODEL if hasattr(settings, "RERANKER_MODEL") else "BAAI/bge-reranker-v2-m3"
        )
        self._local_model = None

    async def rerank(self, query: str, texts: list[str]) -> list[tuple[str, float]]:
        if not texts:
            return []

        if self.use_local:
            return await self._rerank_local(query, texts)

        return await self._rerank_tei(query, texts)

    async def _rerank_tei(self, query: str, texts: list[str]) -> list[tuple[str, float]]:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.endpoint}/rerank",
                    json={"query": query, "texts": texts},
                )
                resp.raise_for_status()
                data = resp.json()

            # TEI rerank returns: [{"index": 0, "score": 0.98, "text": "..."}, ...]
            results: list[tuple[str, float]] = []
            for item in data:
                if isinstance(item, dict):
                    idx = item.get("index", len(results))
                    score = item.get("score", 0.0)
                    if idx < len(texts):
                        results.append((texts[idx], score))
            return sorted(results, key=lambda x: x[1], reverse=True)

        except Exception as e:
            logger.warning("TEI rerank failed, using default order: %s", e)
            return [(t, 1.0 - i * 0.01) for i, t in enumerate(texts)]

    async def _rerank_local(self, query: str, texts: list[str]) -> list[tuple[str, float]]:
        try:
            if self._local_model is None:
                from sentence_transformers import CrossEncoder  # type: ignore[import-untyped]

                self._local_model = CrossEncoder(self.model)

            pairs = [(query, text) for text in texts]
            scores = self._local_model.predict(pairs)  # type: ignore[attr-defined]

            scored = list(zip(texts, scores))
            return sorted(scored, key=lambda x: x[1], reverse=True)

        except Exception as e:
            logger.warning("Local rerank failed, using default order: %s", e)
            return [(t, 1.0 - i * 0.01) for i, t in enumerate(texts)]
