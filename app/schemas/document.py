from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: str
    file_type: str
    file_size: int
    status: str
    allowed_roles: list[str] = ["member"]
    uploaded_by_id: str
    organization_id: str
    collection_id: str | None = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentAccessRequest(BaseModel):
    allowed_roles: list[str] | None = None


class PaginatedDocumentResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    per_page: int
