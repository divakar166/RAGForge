from fastapi import APIRouter, Depends, HTTPException, status
from supabase import AsyncClient

from app.core.deps import OrganizationContext, require_org_role
from app.db.supabase import get_supabase
from app.schemas.role import OrgRoleCreate, OrgRoleResponse, OrgRoleUpdate
from app.services import orgs as orgs_service
from app.services.audit import log_action

router = APIRouter(prefix="/roles", tags=["orgs-roles"])


@router.get("")
async def list_org_roles(
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    roles = await orgs_service.get_org_roles(supabase, ctx.organization["id"])
    return [OrgRoleResponse(**r) for r in roles]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_org_role(
    req: OrgRoleCreate,
    ctx: OrganizationContext = Depends(require_org_role("owner")),
    supabase: AsyncClient = Depends(get_supabase),
):
    role = await orgs_service.create_org_role(
        supabase, ctx.organization["id"],
        name=req.name, description=req.description, permissions=req.permissions,
    )
    if not role:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role name already exists")
    await log_action(
        supabase, ctx.member["user_id"], "role:create",
        resource_type="role", resource_id=role["id"],
        organization_id=ctx.organization["id"],
    )
    return OrgRoleResponse(**role)


@router.get("/{role_id}")
async def get_org_role(
    role_id: str,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    role = await orgs_service.get_org_role(supabase, ctx.organization["id"], role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return OrgRoleResponse(**role)


@router.patch("/{role_id}")
async def update_org_role(
    role_id: str,
    req: OrgRoleUpdate,
    ctx: OrganizationContext = Depends(require_org_role("owner")),
    supabase: AsyncClient = Depends(get_supabase),
):
    role = await orgs_service.update_org_role(
        supabase, ctx.organization["id"], role_id,
        data=req.model_dump(exclude_unset=True),
    )
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found or is a system role")
    await log_action(
        supabase, ctx.member["user_id"], "role:update",
        resource_type="role", resource_id=role_id,
        organization_id=ctx.organization["id"],
    )
    return OrgRoleResponse(**role)


@router.delete("/{role_id}")
async def delete_org_role(
    role_id: str,
    ctx: OrganizationContext = Depends(require_org_role("owner")),
    supabase: AsyncClient = Depends(get_supabase),
):
    deleted = await orgs_service.delete_org_role(supabase, ctx.organization["id"], role_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found or is a system role")
    await log_action(
        supabase, ctx.member["user_id"], "role:delete",
        resource_type="role", resource_id=role_id,
        organization_id=ctx.organization["id"],
    )
    return {"detail": "Role deleted"}
