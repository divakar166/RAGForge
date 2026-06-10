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
    trace_id: str | None = None


class FeedbackRequest(BaseModel):
    trace_id: str = Field(min_length=1)
    score: int = Field(default=1, ge=0, le=1, description="0 (thumbs down) or 1 (thumbs up)")
    comment: str = ""
