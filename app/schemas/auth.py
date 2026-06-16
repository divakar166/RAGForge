from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    org_name: str = Field(min_length=1, max_length=256)
    org_slug: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9-]+$")


class RegisterInviteRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    invitation_token: str = Field(min_length=1)


class LoginRequest(BaseModel):
    username: str = ""
    email: str = ""
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class OrgSelectRequest(BaseModel):
    org_id: str


class OrgBrief(BaseModel):
    id: str
    name: str
    slug: str
    role: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    is_superuser: bool
    organizations: list[OrgBrief] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None
