from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import AsyncClient

from app.core.security import InvalidTokenError, decode_token
from app.db.supabase import get_supabase
from app.rag.vector_store import QdrantStore

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class OrganizationContext:
    organization: dict
    member: dict
    qdrant_store: QdrantStore


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    supabase: AsyncClient = Depends(get_supabase),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    token_type = payload.get("type")

    if not user_id or token_type != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await supabase.table("users").select("*").eq("id", user_id).eq("is_active", True).single().execute()
    user = result.data
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get("is_superuser"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def get_org_context(
    org_id: str,
    user: dict = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
) -> OrganizationContext:
    member_result = await (
        supabase.table("organization_members")
        .select("*, organization:organization_id(*)")
        .eq("organization_id", org_id)
        .eq("user_id", user["id"])
        .eq("is_active", True)
        .single()
        .execute()
    )
    member = member_result.data
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    org = member.get("organization")
    if not org or not org.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is deactivated",
        )

    return OrganizationContext(
        organization=org,
        member=member,
        qdrant_store=QdrantStore(organization_id=org_id),
    )


def require_org_role(*roles: str):
    """Dependency factory: require one of the specified organization roles."""
    async def checker(
        ctx: OrganizationContext = Depends(get_org_context),
        user: dict = Depends(get_current_user),
    ) -> OrganizationContext:
        if ctx.member.get("role") not in roles and not user.get("is_superuser"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of these org roles: {', '.join(roles)}",
            )
        return ctx
    return checker
