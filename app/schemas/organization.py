from datetime import datetime

from pydantic import BaseModel, Field


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    slug: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9-]+$")


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    owner_id: str
    is_active: bool
    member_count: int = 0
    document_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrgUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime | None = None


class MemberUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class InviteRequest(BaseModel):
    email: str = Field(min_length=1)
    role: str = Field(default="member", pattern=r"^(admin|member|viewer)$")


class InviteAcceptRequest(BaseModel):
    token: str = Field(min_length=1)
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class InvitationResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    role: str
    expires_at: datetime
    accepted_at: datetime | None = None
