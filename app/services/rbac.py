import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.permission import Permission
from app.db.models.role import Role
from app.db.models.user import User

logger = logging.getLogger(__name__)


async def get_user_permissions(user: User) -> set[str]:
    codenames: set[str] = set()
    for role in user.roles:
        for perm in role.permissions:
            codenames.add(perm.codename)
    return codenames


async def has_permission(user: User, required_permission: str) -> bool:
    if user.is_superuser:
        return True
    perms = await get_user_permissions(user)
    return required_permission in perms


async def has_any_permission(user: User, required_permissions: list[str]) -> bool:
    if user.is_superuser:
        return True
    perms = await get_user_permissions(user)
    return any(p in perms for p in required_permissions)


# Role CRUD


async def create_role(
    db: AsyncSession,
    name: str,
    description: str | None = None,
    permission_ids: list[str] | None = None,
) -> Role:
    role = Role(name=name, description=description)
    if permission_ids:
        result = await db.execute(
            select(Permission).where(Permission.id.in_([uuid.UUID(pid) for pid in permission_ids]))
        )
        role.permissions = list(result.scalars().all())
    db.add(role)
    await db.flush()
    return role


async def get_role(db: AsyncSession, role_id: str) -> Role | None:
    result = await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.id == uuid.UUID(role_id)))
    return result.scalar_one_or_none()


async def get_roles(db: AsyncSession) -> list[Role]:
    result = await db.execute(select(Role).options(selectinload(Role.permissions)).order_by(Role.name))
    return list(result.scalars().all())


async def update_role(
    db: AsyncSession,
    role_id: str,
    description: str | None = None,
    permission_ids: list[str] | None = None,
) -> Role | None:
    role = await get_role(db, role_id)
    if not role:
        return None
    if description is not None:
        role.description = description
    if permission_ids is not None:
        result = await db.execute(
            select(Permission).where(Permission.id.in_([uuid.UUID(pid) for pid in permission_ids]))
        )
        role.permissions = list(result.scalars().all())
    await db.flush()
    return role


async def delete_role(db: AsyncSession, role_id: str) -> bool:
    role = await get_role(db, role_id)
    if not role or role.is_system_role:
        return False
    await db.delete(role)
    await db.flush()
    return True


# Permission CRUD


async def create_permission(
    db: AsyncSession,
    codename: str,
    name: str,
    resource_type: str,
    action: str,
    description: str | None = None,
) -> Permission:
    perm = Permission(
        codename=codename,
        name=name,
        resource_type=resource_type,
        action=action,
        description=description,
    )
    db.add(perm)
    await db.flush()
    return perm


async def get_permissions(db: AsyncSession) -> list[Permission]:
    result = await db.execute(select(Permission).order_by(Permission.resource_type, Permission.action))
    return list(result.scalars().all())


# User-Role assignment


async def assign_roles(db: AsyncSession, user_id: str, role_ids: list[str]) -> User | None:
    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        return None

    result = await db.execute(select(Role).where(Role.id.in_([uuid.UUID(rid) for rid in role_ids])))
    user.roles = list(result.scalars().all())
    await db.flush()
    return user
