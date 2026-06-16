from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=256)


class ConversationUpdate(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationListItem(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: datetime
