from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    is_superuser: bool
    roles: list[str] = []


class UserUpdate(BaseModel):
    is_active: bool | None = None
    is_superuser: bool | None = None
