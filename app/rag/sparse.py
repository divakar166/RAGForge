"""BM25 sparse vector generation for Qdrant hybrid search."""

from qdrant_client import models as qmodels
from rank_bm25 import BM25Okapi


class BM25SparseEncoder:
    """Converts text to Qdrant-compatible sparse vectors using BM25.

    Uses a shared corpus to compute IDF weights.
    Each token maps to its BM25 score for the given text.
    """

    def __init__(self):
        self.corpus: list[str] = []
        self.bm25: BM25Okapi | None = None
        self._tokenized_corpus: list[list[str]] = []

    def fit(self, texts: list[str]) -> None:
        self.corpus = list(texts)
        self._tokenized_corpus = [t.split() for t in self.corpus]
        self.bm25 = BM25Okapi(self._tokenized_corpus)

    def add_documents(self, texts: list[str]) -> None:
        self.corpus.extend(texts)
        self._tokenized_corpus = [t.split() for t in self.corpus]
        self.bm25 = BM25Okapi(self._tokenized_corpus)

    def encode(self, text: str) -> tuple[list[int], list[float]]:
        """Return (indices, values) suitable for Qdrant SparseVector."""
        if self.bm25 is None:
            return [], []

        tokens = text.split()
        scores = self.bm25.get_scores(tokens)
        token_scores: dict[str, float] = {}

        for token, score in zip(tokens, scores):
            if score > 0:
                token_scores[token] = max(token_scores.get(token, 0), score)

        # Hash tokens to integer indices
        indices: list[int] = [hash(t) & 0x7FFFFFFF for t in token_scores.keys()]
        values: list[float] = list(token_scores.values())

        return indices, values

    def encode_for_qdrant(self, text: str) -> qmodels.SparseVector:
        indices, values = self.encode(text)
        return qmodels.SparseVector(indices=indices, values=values)

    @property
    def is_fitted(self) -> bool:
        return self.bm25 is not None
