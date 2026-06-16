import logging

from fastapi import APIRouter, Depends, Request
from supabase import AsyncClient

from app.core.deps import OrganizationContext, require_org_role
from app.db.supabase import get_supabase
from app.schemas.organization import InvitationResponse, InviteRequest
from app.services import orgs as orgs_service
from app.services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invites", tags=["orgs-invites"])


@router.post("")
async def invite_member(
    req: InviteRequest,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
    request: Request = None,
):
    invitation = await orgs_service.invite_member(
        supabase, ctx.organization["id"], req.email, req.role, ctx.member["user_id"],
    )

    await log_action(
        supabase, ctx.member["user_id"], "invite:create",
        resource_type="invitation", resource_id=invitation["id"],
        details={"email": req.email, "role": req.role},
        organization_id=ctx.organization["id"],
    )

    base_url = f"{request.url.scheme}://{request.url.hostname}" if request else "http://localhost:3000"
    if request and request.url.port:
        base_url += f":{request.url.port}"
    invite_url = f"{base_url}/invite?token={invitation['token']}"
    logger.info("Invitation created — URL: %s", invite_url)

    return InvitationResponse(
        id=invitation["id"],
        organization_id=invitation["organization_id"],
        email=invitation["email"],
        role=invitation["role"],
        token=invitation["token"],
        expires_at=invitation.get("expires_at"),
    )


@router.get("")
async def list_invitations(
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    result = await (
        supabase.table("invitations")
        .select("*")
        .eq("organization_id", ctx.organization["id"])
        .is_("accepted_at", "null")
        .execute()
    )
    return [
        InvitationResponse(
            id=i["id"],
            organization_id=i["organization_id"],
            email=i["email"],
            role=i["role"],
            token=i["token"],
            expires_at=i.get("expires_at"),
            accepted_at=i.get("accepted_at"),
        )
        for i in (result.data or [])
    ]
