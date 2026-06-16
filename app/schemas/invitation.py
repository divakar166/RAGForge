from pydantic import BaseModel


class InviteVerifyResponse(BaseModel):
    valid: bool
    email: str
    role: str
    org_name: str
