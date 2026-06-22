import logging
import secrets
from datetime import datetime, timedelta, timezone

from supabase import AsyncClient

logger = logging.getLogger(__name__)

DEFAULT_ROLES = [
    {
        "name": "owner",
        "description": "Organization owner with full access",
        "permissions": [
            "documents:create", "documents:read", "documents:update", "documents:delete",
            "documents:download", "search:query", "collections:manage", "members:manage",
            "invites:manage", "audit:view", "evaluate:run", "roles:manage", "settings:manage",
        ],
        "is_system": True,
    },
    {
        "name": "admin",
        "description": "Full org access",
        "permissions": [
            "documents:create", "documents:read", "documents:update", "documents:delete",
            "documents:download", "search:query", "collections:manage", "members:manage",
            "invites:manage", "audit:view", "evaluate:run", "roles:manage", "settings:manage",
        ],
        "is_system": True,
    },
    {
        "name": "member",
        "description": "Can manage documents and search",
        "permissions": [
            "documents:create", "documents:read", "documents:update", "documents:delete",
            "documents:download", "search:query", "collections:manage",
        ],
        "is_system": True,
    },
    {
        "name": "viewer",
        "description": "Read-only access",
        "permissions": ["documents:read", "documents:download", "search:query"],
        "is_system": True,
    },
]


async def seed_default_roles(supabase: AsyncClient, org_id: str):
    for role in DEFAULT_ROLES:
        existing = await supabase.table("organization_roles").select("id").eq("organization_id", org_id).eq("name", role["name"]).limit(1).execute()
        if existing.data:
            continue
        await supabase.table("organization_roles").insert({
            "organization_id": org_id,
            "name": role["name"],
            "description": role["description"],
            "permissions": role["permissions"],
            "is_system": role["is_system"],
        }).execute()


async def get_org_roles(supabase: AsyncClient, org_id: str) -> list[dict]:
    roles_resp = await supabase.table("organization_roles").select("*").eq("organization_id", org_id).order("name").execute()
    roles = roles_resp.data or []
    for r in roles:
        member_count = await supabase.table("organization_members").select("id", count="exact").eq("organization_id", org_id).eq("role", r["name"]).execute()
        r["member_count"] = member_count.count if hasattr(member_count, 'count') else 0
    return roles


async def get_org_role(supabase: AsyncClient, org_id: str, role_id: str) -> dict | None:
    resp = await supabase.table("organization_roles").select("*").eq("id", role_id).eq("organization_id", org_id).single().execute()
    return resp.data


async def create_org_role(supabase: AsyncClient, org_id: str, name: str, description: str | None, permissions: list[str]) -> dict | None:
    existing = await supabase.table("organization_roles").select("id").eq("organization_id", org_id).eq("name", name).limit(1).execute()
    if existing.data:
        return None
    resp = await supabase.table("organization_roles").insert({
        "organization_id": org_id,
        "name": name,
        "description": description,
        "permissions": permissions,
        "is_system": False,
    }).select("*").execute()
    return resp.data[0] if resp.data else None


async def update_org_role(supabase: AsyncClient, org_id: str, role_id: str, data: dict) -> dict | None:
    role = await get_org_role(supabase, org_id, role_id)
    if not role or role.get("is_system"):
        return None
    update_data = {k: v for k, v in data.items() if v is not None}
    if not update_data:
        return role
    resp = await supabase.table("organization_roles").update(update_data).eq("id", role_id).eq("organization_id", org_id).select("*").execute()
    return resp.data[0] if resp.data else None


async def delete_org_role(supabase: AsyncClient, org_id: str, role_id: str) -> bool:
    role = await get_org_role(supabase, org_id, role_id)
    if not role or role.get("is_system"):
        return False
    await supabase.table("organization_roles").delete().eq("id", role_id).eq("organization_id", org_id).execute()
    return True


async def validate_role_name(supabase: AsyncClient, org_id: str, role_name: str) -> bool:
    resp = await supabase.table("organization_roles").select("id").eq("organization_id", org_id).eq("name", role_name).limit(1).execute()
    return bool(resp.data)


async def create_organization(supabase: AsyncClient, name: str, slug: str, owner_id: str) -> dict | None:
    existing = await supabase.table("organizations").select("id").eq("slug", slug).limit(1).execute()
    if existing.data:
        return None

    org_resp = await (
        supabase.table("organizations")
        .insert({"name": name, "slug": slug, "owner_id": owner_id})
        .select("*")
        .execute()
    )
    return org_resp.data[0] if org_resp.data else None


async def get_organization(supabase: AsyncClient, org_id: str) -> dict | None:
    org_resp = await supabase.table("organizations").select("*").eq("id", org_id).single().execute()
    return org_resp.data


async def update_organization(supabase: AsyncClient, org_id: str, data: dict) -> dict | None:
    org_resp = await (
        supabase.table("organizations")
        .update(data)
        .eq("id", org_id)
        .select("*")
        .execute()
    )
    return org_resp.data[0] if org_resp.data else None


async def delete_organization(supabase: AsyncClient, org_id: str) -> bool:
    await supabase.table("organizations").delete().eq("id", org_id).execute()
    return True


async def get_members(supabase: AsyncClient, org_id: str) -> list[dict]:
    members_resp = await (
        supabase.table("organization_members")
        .select("*, user:user_id(id, email, username, is_active)")
        .eq("organization_id", org_id)
        .eq("is_active", True)
        .order("created_at")
        .execute()
    )
    return [
        {
            "id": m["id"],
            "user_id": m["user_id"],
            "email": m.get("user", {}).get("email"),
            "username": m.get("user", {}).get("username"),
            "role": m["role"],
            "is_active": m["is_active"],
            "created_at": m.get("created_at"),
        }
        for m in (members_resp.data or [])
    ]


async def update_member_role(
    supabase: AsyncClient, org_id: str, user_id: str,
    role: str = None, is_active: bool = None,
) -> dict | None:
    update_data = {}
    if role is not None:
        update_data["role"] = role
    if is_active is not None:
        update_data["is_active"] = is_active
    if not update_data:
        return None

    member_resp = await (
        supabase.table("organization_members")
        .update(update_data)
        .eq("user_id", user_id)
        .eq("organization_id", org_id)
        .select("*")
        .execute()
    )
    return member_resp.data[0] if member_resp.data else None


async def remove_member(supabase: AsyncClient, org_id: str, user_id: str) -> bool:
    await supabase.table("organization_members").delete().eq("user_id", user_id).eq("organization_id", org_id).execute()
    return True


async def verify_invite_token(supabase: AsyncClient, token: str) -> dict | None:
    invite_resp = await (
        supabase.table("invitations")
        .select("*, organization:organization_id(name)")
        .eq("token", token)
        .is_("accepted_at", "null")
        .single()
        .execute()
    )
    invitation = invite_resp.data
    if not invitation:
        return None

    if datetime.fromisoformat(invitation["expires_at"].replace("Z", "+00:00")) < datetime.now(timezone.utc):
        return None

    return invitation


async def invite_member(supabase: AsyncClient, org_id: str, email: str, role: str, invited_by_id: str) -> dict:
    token = secrets.token_urlsafe(48)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    invite_resp = await (
        supabase.table("invitations")
        .insert({
            "organization_id": org_id,
            "email": email,
            "token": token,
            "role": role,
            "invited_by_id": invited_by_id,
            "expires_at": expires_at,
        })
        .select("*")
        .execute()
    )
    return invite_resp.data[0]


async def get_org_stats(supabase: AsyncClient, org_id: str) -> dict:
    members_resp = await (
        supabase.table("organization_members")
        .select("id", count="exact")
        .eq("organization_id", org_id)
        .eq("is_active", True)
        .execute()
    )
    member_count = members_resp.count if hasattr(members_resp, 'count') else len(members_resp.data or [])

    docs_resp = await (
        supabase.table("documents")
        .select("id", count="exact")
        .eq("organization_id", org_id)
        .execute()
    )
    doc_count = docs_resp.count if hasattr(docs_resp, 'count') else len(docs_resp.data or [])

    return {
        "member_count": member_count,
        "document_count": doc_count,
    }
