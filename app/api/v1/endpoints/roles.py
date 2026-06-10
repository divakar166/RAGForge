from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.role import (
    PermissionResponse,
    RoleCreate,
    RoleResponse,
)
from app.services import rbac as rbac_service
from app.services.audit import log_action

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    roles = await rbac_service.get_roles(db)
    return [
        RoleResponse(
            id=str(r.id),
            name=r.name,
            description=r.description,
            is_system_role=r.is_system_role,
            permissions=[p.codename for p in r.permissions],
            created_at=r.created_at.isoformat() if r.created_at else None,
            updated_at=r.updated_at.isoformat() if r.updated_at else None,
        )
        for r in roles
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_role(
    req: RoleCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    role = await rbac_service.create_role(db, req.name, req.description, req.permission_ids)
    await log_action(db, str(admin.id), "role:create", "role", str(role.id), req.model_dump())
    return RoleResponse(
        id=str(role.id),
        name=role.name,
        description=role.description,
        is_system_role=role.is_system_role,
        permissions=[p.codename for p in role.permissions],
        created_at=role.created_at.isoformat() if role.created_at else None,
        updated_at=role.updated_at.isoformat() if role.updated_at else None,
    )


@router.get("/permissions")
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    perms = await rbac_service.get_permissions(db)
    return [
        PermissionResponse(
            id=str(p.id),
            codename=p.codename,
            name=p.name,
            description=p.description,
            resource_type=p.resource_type,
            action=p.action,
        )
        for p in perms
    ]


@router.delete("/{role_id}")
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    deleted = await rbac_service.delete_role(db, role_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found or is system role",
        )
    await log_action(db, str(admin.id), "role:delete", "role", role_id)
    return {"detail": "Role deleted"}
