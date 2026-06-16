from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: str
    file_type: str
    file_size: int
    status: str
    is_public_in_org: bool
    uploaded_by_id: str
    organization_id: str
    collection_id: str | None = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentAccessRequest(BaseModel):
    is_public_in_org: bool | None = None
    allowed_user_ids: list[str] = []


class PaginatedDocumentResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    per_page: int
