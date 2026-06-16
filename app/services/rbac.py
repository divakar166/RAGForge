"""Replaced by organization-level role checks via deps.require_org_role.

This file is kept as a stub during migration. Import from app.core.deps instead.

Usage:
    from app.core.deps import get_org_context, require_org_role

    @router.post("/docs")
    async def upload(ctx = Depends(require_org_role("owner", "admin", "member"))):
        ...
"""

from app.db.models.user import User


async def has_any_permission(user: User, _permissions: list[str]) -> bool:
    """Deprecated. Use require_org_role() instead."""
    return bool(user.is_superuser)
