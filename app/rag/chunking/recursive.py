import re

from app.core.config import settings
from app.rag.chunking import Chunk, ChunkingStrategy


class RecursiveChunking(ChunkingStrategy):
    """Structure-aware recursive splitter with breadcrumb context."""

    SEPARATORS = [r"\n#{1,6}\s+", r"\n\n", r"\n", r"\. ", r" "]

    def __init__(self, chunk_size: int | None = None, overlap: int | None = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.overlap = overlap or settings.CHUNK_OVERLAP

    def chunk(self, text: str, doc_title: str = "") -> list[Chunk]:
        sections = self._extract_sections_with_paths(text)
        chunks: list[Chunk] = []
        char_offset = 0

        for section_path, section_text in sections:
            raw_chunks = self._split_text(section_text)
            for i, raw in enumerate(raw_chunks):
                prefix = f"[{doc_title}]" if doc_title else ""
                if section_path:
                    prefix += f" [{section_path}]"
                content = f"{prefix} {raw}" if prefix else raw
                chunks.append(
                    Chunk(
                        content=content,
                        index=len(chunks),
                        strategy="recursive",
                        section_path=section_path or None,
                        start_char=char_offset,
                        end_char=char_offset + len(raw),
                    )
                )
                char_offset += len(raw)

        return chunks

    def _extract_sections_with_paths(self, text: str) -> list[tuple[str, str]]:
        lines = text.split("\n")
        sections: list[tuple[str, str]] = []
        path: list[str] = []
        buf: list[str] = []

        for line in lines:
            m = re.match(r"^(#{1,6})\s+(.+)$", line)
            if m:
                if buf:
                    sections.append((" > ".join(path), "\n".join(buf)))
                    buf = []
                level = len(m.group(1))
                title = m.group(2).strip()
                path = path[: level - 1] + [title]
            else:
                buf.append(line)

        if buf:
            sections.append((" > ".join(path), "\n".join(buf)))
        return sections

    def _split_text(self, text: str) -> list[str]:
        if not text.strip():
            return []

        for sep in self.SEPARATORS:
            if self._token_count(text) <= self.chunk_size:
                return [text]

            parts = re.split(sep, text)
            if len(parts) <= 1:
                continue

            result: list[str] = []
            buf = ""
            for part in parts:
                if not part.strip():
                    continue
                candidate = f"{buf}{' ' if buf else ''}{part}".strip()
                if self._token_count(candidate) > self.chunk_size:
                    if buf:
                        result.append(buf)
                    buf = part
                else:
                    buf = candidate
            if buf:
                result.append(buf)
            return result if result else [text]

        return [text]

    def _token_count(self, text: str) -> int:
        return len(text) // 4
