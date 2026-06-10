from pydantic import BaseModel, Field


class PermissionCreate(BaseModel):
    codename: str = Field(min_length=3, max_length=128)
    name: str = Field(min_length=3, max_length=256)
    description: str | None = None
    resource_type: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=64)


class PermissionResponse(BaseModel):
    id: str
    codename: str
    name: str
    description: str | None = None
    resource_type: str
    action: str


class RoleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=128)
    description: str | None = None
    permission_ids: list[str] = []


class RoleUpdate(BaseModel):
    description: str | None = None
    permission_ids: list[str] | None = None


class RoleResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    is_system_role: bool
    permissions: list[PermissionResponse] = []


class AssignRolesRequest(BaseModel):
    role_ids: list[str]
