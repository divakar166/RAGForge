from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Chunk:
    content: str
    index: int
    strategy: str
    section_path: str | None = None
    start_char: int = 0
    end_char: int = 0
    metadata: dict = field(default_factory=dict)


class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, text: str, doc_title: str = "") -> list[Chunk]: ...
