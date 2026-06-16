"""Cross-encoder reranking — local sentence-transformers or identity pass-through."""

import logging

logger = logging.getLogger(__name__)


class Reranker:
    def __init__(
        self,
        use_local: bool = False,
        model: str = "",
    ):
        self.use_local = use_local
        self.model = model or "BAAI/bge-reranker-v2-m3"
        self._local_model = None

    async def rerank(self, query: str, texts: list[str]) -> list[tuple[str, float]]:
        if not texts:
            return []

        if self.use_local:
            return await self._rerank_local(query, texts)

        return self._passthrough(texts)

    async def _rerank_local(self, query: str, texts: list[str]) -> list[tuple[str, float]]:
        try:
            if self._local_model is None:
                from sentence_transformers import CrossEncoder

                self._local_model = CrossEncoder(self.model)

            pairs = [(query, text) for text in texts]
            scores = self._local_model.predict(pairs)

            scored = list(zip(texts, scores))
            return sorted(scored, key=lambda x: x[1], reverse=True)

        except Exception as e:
            logger.warning("Local rerank failed, using default order: %s", e)
            return self._passthrough(texts)

    def _passthrough(self, texts: list[str]) -> list[tuple[str, float]]:
        return [(t, 1.0 - i * 0.01) for i, t in enumerate(texts)]
