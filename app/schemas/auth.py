from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=3, max_length=64, alias="username")
    password: str = Field(min_length=8, max_length=128)

    model_config = {"populate_by_name": True}


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
