from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import OrganizationContext, require_org_role
from app.db.models.invitation import Invitation
from app.db.session import get_db
from app.schemas.organization import InvitationResponse, InviteRequest
from app.services import orgs as orgs_service
from app.services.audit import log_action

router = APIRouter(prefix="/invites", tags=["orgs-invites"])


@router.post("")
async def invite_member(
    req: InviteRequest,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    invitation = await orgs_service.invite_member(
        db, ctx.organization.id, req.email, req.role, ctx.member.user_id,
    )

    await log_action(
        db, ctx.member.user_id, "invite:create",
        resource_type="invitation", resource_id=invitation.id,
        details={"email": req.email, "role": req.role},
        organization_id=ctx.organization.id,
    )

    return InvitationResponse(
        id=str(invitation.id),
        organization_id=str(invitation.organization_id),
        email=invitation.email,
        role=invitation.role,
        expires_at=invitation.expires_at,
    )


@router.get("")
async def list_invitations(
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invitation).where(
            Invitation.organization_id == ctx.organization.id,
            Invitation.accepted_at.is_(None),
        )
    )
    invitations = result.scalars().all()
    return [
        InvitationResponse(
            id=str(i.id),
            organization_id=str(i.organization_id),
            email=i.email,
            role=i.role,
            expires_at=i.expires_at,
            accepted_at=i.accepted_at,
        )
        for i in invitations
    ]
