"""Deprecated — roles are now managed via organization memberships.

See app/api/v1/endpoints/orgs/members.py for member management.
"""

from fastapi import APIRouter, Depends

from app.core.deps import get_current_admin
from app.db.models.user import User

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("")
async def list_roles(admin: User = Depends(get_current_admin)):
    return {"message": "Deprecated. Use /api/v1/orgs/{org_id}/members instead."}
