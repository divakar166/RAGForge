from fastapi import APIRouter, Depends, HTTPException, status
from supabase import AsyncClient

from app.core.deps import OrganizationContext, require_org_role
from app.db.supabase import get_supabase
from app.schemas.organization import MemberResponse, MemberUpdate
from app.services import orgs as orgs_service
from app.services.audit import log_action

router = APIRouter(prefix="/members", tags=["orgs-members"])


@router.get("")
async def list_members(
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    members = await orgs_service.get_members(supabase, ctx.organization["id"])
    return [MemberResponse(**m) for m in members]


@router.patch("/{user_id}")
async def update_member(
    user_id: str,
    req: MemberUpdate,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    updated = await orgs_service.update_member_role(
        supabase, ctx.organization["id"], user_id,
        role=req.role, is_active=req.is_active,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    await log_action(
        supabase, ctx.member["user_id"], "member:update",
        resource_type="user", resource_id=user_id,
        details={"role": req.role, "is_active": req.is_active},
        organization_id=ctx.organization["id"],
    )
    return {"detail": "Member updated"}


@router.delete("/{user_id}")
async def remove_member(
    user_id: str,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    if user_id == ctx.organization["owner_id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the organization owner")

    removed = await orgs_service.remove_member(supabase, ctx.organization["id"], user_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    await log_action(
        supabase, ctx.member["user_id"], "member:remove",
        resource_type="user", resource_id=user_id,
        organization_id=ctx.organization["id"],
    )
    return {"detail": "Member removed"}
