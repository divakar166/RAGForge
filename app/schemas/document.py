from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    title: str
    file_type: str
    file_size: int
    status: str
    is_public: bool
    owner_id: str
    created_at: datetime
    updated_at: datetime


class DocumentAccessRequest(BaseModel):
    is_public: bool | None = None
    allowed_role_ids: list[str] = []
    allowed_user_ids: list[str] = []
