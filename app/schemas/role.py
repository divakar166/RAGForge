from pydantic import BaseModel


class AssignRolesRequest(BaseModel):
    role_ids: list[str]
