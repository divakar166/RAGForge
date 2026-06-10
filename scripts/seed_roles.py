"""Seed default roles and permissions."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models.permission import Permission, RolePermission
from app.db.models.role import Role, UserRole
from app.db.models.user import User

DEFAULT_PERMISSIONS = [
    {"codename": "document:create", "name": "Create Documents", "resource_type": "document", "action": "create"},
    {"codename": "document:read", "name": "Read Documents", "resource_type": "document", "action": "read"},
    {"codename": "document:update", "name": "Update Documents", "resource_type": "document", "action": "update"},
    {"codename": "document:delete", "name": "Delete Documents", "resource_type": "document", "action": "delete"},
    {"codename": "search:query", "name": "Search Documents", "resource_type": "search", "action": "query"},
    {"codename": "users:manage", "name": "Manage Users", "resource_type": "users", "action": "manage"},
    {"codename": "roles:manage", "name": "Manage Roles", "resource_type": "roles", "action": "manage"},
    {"codename": "admin:full", "name": "Full Admin Access", "resource_type": "admin", "action": "*"},
    {"codename": "evaluate:run", "name": "Run Evaluations", "resource_type": "evaluate", "action": "run"},
]

ROLES_CONFIG = {
    "admin": {
        "description": "Full system access",
        "is_system_role": True,
        "permissions": ["*"],
    },
    "editor": {
        "description": "Can upload and manage documents",
        "is_system_role": True,
        "permissions": ["document:create", "document:read", "document:update", "document:delete", "search:query"],
    },
    "viewer": {
        "description": "Can search and read documents",
        "is_system_role": True,
        "permissions": ["document:read", "search:query"],
    },
}


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        # Check if already seeded
        existing = await db.execute(select(Role).limit(1))
        if existing.scalar_one_or_none():
            print("Roles already seeded, skipping.")
            return

        # Create permissions
        perm_map = {}
        for p_def in DEFAULT_PERMISSIONS:
            perm = Permission(**p_def)
            db.add(perm)
            await db.flush()
            perm_map[p_def["codename"]] = perm

        # Create roles
        for role_name, role_def in ROLES_CONFIG.items():
            role = Role(
                name=role_name,
                description=role_def["description"],
                is_system_role=role_def["is_system_role"],
            )
            db.add(role)
            await db.flush()

            if role_def["permissions"] == ["*"]:
                permissions = list(perm_map.values())
            else:
                permissions = [
                    perm_map[pc]
                    for pc in role_def["permissions"]
                    if pc in perm_map
                ]

            for perm in permissions:
                db.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=perm.id,
                    )
                )
                
        await db.commit()
        print("Seeded roles and permissions successfully!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
