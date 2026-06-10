from app.core.config import settings
from app.rag.chunking import Chunk
from app.rag.chunking.recursive import RecursiveChunking
from app.rag.chunking.semantic import SemanticChunking


class ChunkingPipeline:
    """Selects and runs chunking strategy based on document type or config."""

    STRATEGY_MAP: dict[str, str] = {
        "md": "recursive",
        "html": "recursive",
        "pdf": "recursive",
        "txt": "semantic",
        "docx": "semantic",
    }

    def __init__(self, embed_fn=None):
        self.embed_fn = embed_fn
        self._recursive = RecursiveChunking()
        self._semantic = SemanticChunking(embed_fn) if embed_fn else None

    def chunk(
        self,
        text: str,
        doc_title: str = "",
        file_type: str = "txt",
        strategy: str | None = None,
    ) -> list[Chunk]:
        selected = strategy or self.STRATEGY_MAP.get(file_type, settings.CHUNK_DEFAULT_STRATEGY)

        if selected == "semantic" and self._semantic:
            chunks = self._semantic.chunk(text, doc_title)
        else:
            chunks = self._recursive.chunk(text, doc_title)

        return chunks

    def get_available_strategies(self) -> list[str]:
        strategies = ["recursive"]
        if self._semantic:
            strategies.append("semantic")
        return strategies
