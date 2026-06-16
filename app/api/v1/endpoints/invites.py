import logging

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import AsyncClient

from app.db.supabase import get_supabase
from app.schemas.invitation import InviteVerifyResponse
from app.services.orgs import verify_invite_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invites", tags=["invites"])


@router.get("/verify/{token}")
async def verify_invite(token: str, supabase: AsyncClient = Depends(get_supabase)):
    invitation = await verify_invite_token(supabase, token)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invitation")

    return InviteVerifyResponse(
        valid=True,
        email=invitation["email"],
        role=invitation["role"],
        org_name=invitation.get("organization", {}).get("name", ""),
    )
