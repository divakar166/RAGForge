from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: str
    file_type: str
    file_size: int
    status: str
    is_public: bool
    owner_id: UUID
    allowed_role_ids: list[str] = []
    allowed_user_ids: list[str] = []
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentAccessRequest(BaseModel):
    is_public: bool | None = None
    allowed_role_ids: list[str] = []
    allowed_user_ids: list[str] = []


class PaginatedDocumentResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    per_page: int
