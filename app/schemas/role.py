from datetime import datetime

from pydantic import BaseModel, Field


PERMISSION_OPTIONS = [
    "documents:create",
    "documents:read",
    "documents:update",
    "documents:delete",
    "documents:download",
    "search:query",
    "collections:manage",
    "members:manage",
    "invites:manage",
    "audit:view",
    "evaluate:run",
    "roles:manage",
    "settings:manage",
]


class OrgRoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_ -]+$")
    description: str | None = None
    permissions: list[str] = Field(default_factory=lambda: ["documents:read", "search:query"])


class OrgRoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


class OrgRoleResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None = None
    permissions: list[str]
    is_system: bool
    member_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
