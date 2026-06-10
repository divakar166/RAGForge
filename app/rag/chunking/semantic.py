import numpy as np

from app.core.config import settings
from app.rag.chunking import Chunk, ChunkingStrategy


class SemanticChunking(ChunkingStrategy):
    """Splits text at topic boundaries using embedding similarity.

    Each sentence is embedded; adjacent pairs with low cosine similarity
    mark chunk boundaries (default: bottom 5th percentile of distances).
    """

    def __init__(
        self,
        embed_fn,
        chunk_size: int | None = None,
        threshold_percentile: float = 95,
    ):
        self.embed_fn = embed_fn
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.threshold_percentile = threshold_percentile

    def chunk(self, text: str, doc_title: str = "") -> list[Chunk]:
        sentences = self._split_sentences(text)
        if len(sentences) <= 1:
            return [
                Chunk(
                    content=text.strip(),
                    index=0,
                    strategy="semantic",
                    start_char=0,
                    end_char=len(text),
                )
            ]

        embeddings = self.embed_fn(sentences).get("embeddings", [])

        if len(embeddings) < 2:
            return self._fallback(sentences, doc_title)

        similarities = []
        for i in range(len(embeddings) - 1):
            a = np.array(embeddings[i], dtype=np.float32)
            b = np.array(embeddings[i + 1], dtype=np.float32)
            sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)
            similarities.append(float(sim))

        if not similarities:
            return self._fallback(sentences, doc_title)

        threshold = float(np.percentile(similarities, 100 - self.threshold_percentile))

        chunks: list[Chunk] = []
        buf: list[str] = []
        char_offset = 0

        for i, sent in enumerate(sentences):
            buf.append(sent)
            if i < len(similarities) and similarities[i] < threshold:
                if self._token_count(" ".join(buf)) >= self.chunk_size // 2:
                    content = " ".join(buf)
                    chunks.append(
                        Chunk(
                            content=content,
                            index=len(chunks),
                            strategy="semantic",
                            start_char=char_offset,
                            end_char=char_offset + len(content),
                        )
                    )
                    char_offset += len(content)
                    buf = []

        if buf:
            content = " ".join(buf)
            chunks.append(
                Chunk(
                    content=content,
                    index=len(chunks),
                    strategy="semantic",
                    start_char=char_offset,
                    end_char=char_offset + len(content),
                )
            )

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        import re

        raw = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in raw if s.strip()]

    def _fallback(self, sentences: list[str], doc_title: str) -> list[Chunk]:
        return [
            Chunk(
                content=" ".join(sentences),
                index=0,
                strategy="semantic",
                start_char=0,
                end_char=len(" ".join(sentences)),
            )
        ]

    def _token_count(self, text: str) -> int:
        return len(text) // 4
