from datetime import datetime

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str = ""


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None


class CollectionResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str
    is_public: bool
    document_count: int = 0
    created_at: datetime
    updated_at: datetime
