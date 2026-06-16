import logging
from datetime import datetime, timezone

from supabase import AsyncClient

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import RegisterRequest

logger = logging.getLogger(__name__)


async def register_user(supabase: AsyncClient, req: RegisterRequest) -> tuple[dict, dict]:
    existing = await (
        supabase.table("users")
        .select("id")
        .or_(f"email.eq.{req.email},username.eq.{req.username}")
        .limit(1)
        .execute()
    )
    if existing.data:
        raise ValueError("Email or username already taken")

    user_resp = await (
        supabase.table("users")
        .insert({
            "email": req.email,
            "username": req.username,
            "hashed_password": hash_password(req.password),
        })
        .select("*")
        .execute()
    )
    user = user_resp.data[0]

    org_resp = await (
        supabase.table("organizations")
        .insert({
            "name": req.org_name,
            "slug": req.org_slug,
            "owner_id": user["id"],
        })
        .select("*")
        .execute()
    )
    org = org_resp.data[0]

    await supabase.table("organization_members").insert({
        "organization_id": org["id"],
        "user_id": user["id"],
        "role": "owner",
    }).execute()

    return user, org


async def register_with_invitation(
    supabase: AsyncClient,
    token: str,
    username: str,
    password: str,
    email: str,
) -> tuple[dict, dict, dict]:
    invite_resp = await (
        supabase.table("invitations")
        .select("*, organization:organization_id(*)")
        .eq("token", token)
        .is_("accepted_at", "null")
        .single()
        .execute()
    )
    invitation = invite_resp.data
    if not invitation:
        raise ValueError("Invalid or expired invitation token")

    if datetime.fromisoformat(invitation["expires_at"].replace("Z", "+00:00")) < datetime.now(timezone.utc):
        raise ValueError("Invitation has expired")

    existing = await supabase.table("users").select("id").eq("email", email).limit(1).execute()
    if existing.data:
        raise ValueError("Email already registered")

    user_resp = await (
        supabase.table("users")
        .insert({
            "email": email,
            "username": username,
            "hashed_password": hash_password(password),
        })
        .select("*")
        .execute()
    )
    user = user_resp.data[0]

    member_resp = await (
        supabase.table("organization_members")
        .insert({
            "organization_id": invitation["organization_id"],
            "user_id": user["id"],
            "role": invitation["role"],
        })
        .select("*")
        .execute()
    )
    member = member_resp.data[0]

    await supabase.table("invitations").update({
        "accepted_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", invitation["id"]).execute()

    return user, invitation.get("organization"), member


async def authenticate_user(supabase: AsyncClient, username: str, password: str) -> dict | None:
    user_resp = await (
        supabase.table("users")
        .select("*")
        .or_(f"username.eq.{username},email.eq.{username}")
        .limit(1)
        .execute()
    )
    user = user_resp.data[0] if user_resp.data else None
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user


async def login(supabase: AsyncClient, username: str, password: str) -> dict | None:
    user = await authenticate_user(supabase, username, password)
    if not user:
        return None

    members_resp = await (
        supabase.table("organization_members")
        .select("*")
        .eq("user_id", user["id"])
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    extra_claims = {}
    if members_resp.data:
        primary = members_resp.data[0]
        extra_claims["org_id"] = primary["organization_id"]
        extra_claims["org_role"] = primary["role"]

    return {
        "access_token": create_access_token(user["id"], extra_claims=extra_claims),
        "refresh_token": create_refresh_token(user["id"]),
        "token_type": "bearer",
    }


async def login_with_org(supabase: AsyncClient, user_id: str, org_id: str) -> dict | None:
    member_resp = await (
        supabase.table("organization_members")
        .select("*, organization:organization_id(*)")
        .eq("organization_id", org_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .single()
        .execute()
    )
    member = member_resp.data
    if not member:
        return None

    org = member.get("organization", {})

    return {
        "access_token": create_access_token(
            user_id,
            extra_claims={
                "org_id": org_id,
                "org_role": member["role"],
                "org_name": org.get("name", ""),
            },
        ),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
    }


async def refresh_access_token(supabase: AsyncClient, refresh_token: str) -> dict | None:
    try:
        payload = decode_token(refresh_token)
    except InvalidTokenError:
        return None

    user_id = payload.get("sub")
    token_type = payload.get("type")

    if not user_id or token_type != "refresh":
        return None

    user_resp = await (
        supabase.table("users")
        .select("*")
        .eq("id", user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    user = user_resp.data[0] if user_resp.data else None
    if not user:
        return None

    members_resp = await (
        supabase.table("organization_members")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    extra_claims = {}
    if members_resp.data:
        primary = members_resp.data[0]
        extra_claims["org_id"] = primary["organization_id"]
        extra_claims["org_role"] = primary["role"]

    return {
        "access_token": create_access_token(user_id, extra_claims=extra_claims),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
    }


async def get_user_orgs(supabase: AsyncClient, user_id: str) -> list[dict]:
    members_resp = await (
        supabase.table("organization_members")
        .select("*, organization:organization_id(*)")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .execute()
    )
    members = members_resp.data or []
    return [
        {
            "id": m.get("organization", {}).get("id"),
            "name": m.get("organization", {}).get("name"),
            "slug": m.get("organization", {}).get("slug"),
            "role": m["role"],
        }
        for m in members
        if m.get("organization")
    ]
