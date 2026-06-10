from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)


class RAGRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    stream: bool = False


class ChunkResult(BaseModel):
    content: str
    score: float
    document_id: str
    doc_title: str
    chunk_index: int
    section_path: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[ChunkResult]


class RAGResponse(BaseModel):
    query: str
    answer: str
    citations: list[ChunkResult]
    model: str
