from datetime import datetime

from pydantic import BaseModel


class RoleBrief(BaseModel):
    id: str
    name: str
    permissions: list[str] = []


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    roles: list[RoleBrief] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserUpdate(BaseModel):
    is_active: bool | None = None
    is_superuser: bool | None = None
