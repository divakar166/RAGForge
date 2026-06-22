from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: str
    file_type: str
    file_size: int
    status: str
    classification: str = "internal"
    allowed_roles: list[str] = ["member"]
    uploaded_by_id: str
    organization_id: str
    collection_id: str | None = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentAccessRequest(BaseModel):
    allowed_roles: list[str] | None = None


class DocumentUpdateRequest(BaseModel):
    collection_id: str | None = None
    title: str | None = None
    classification: str | None = None


class PaginatedDocumentResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    per_page: int
