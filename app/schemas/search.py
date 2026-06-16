from datetime import datetime

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)


class RAGRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    stream: bool = False
    conversation_id: str | None = None


class SearchResultItem(BaseModel):
    score: float
    text: str
    content: str = ""
    document_id: str
    document_filename: str
    doc_title: str = ""
    metadata: dict = {}
    chunk_index: int = 0
    section_path: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total: int = 0


class RAGResponse(BaseModel):
    query: str
    answer: str
    citations: list[SearchResultItem]
    model: str
    trace_id: str | None = None


class FeedbackRequest(BaseModel):
    trace_id: str = Field(min_length=1)
    score: int | str = Field(default=1, description="0/1 or 'thumbs_up'/'thumbs_down'")
    comment: str = ""


class ConversationResponse(BaseModel):
    id: str
    query: str
    answer: str
    citations: dict | None = None
    feedback_score: int | None = None
    created_at: datetime


class ConversationMessage(BaseModel):
    id: str
    query: str
    answer: str
    citations: dict | None = None
    feedback_score: int | None = None
    created_at: datetime
