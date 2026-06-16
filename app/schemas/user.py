from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    is_superuser: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserUpdate(BaseModel):
    is_active: bool | None = None
    is_superuser: bool | None = None
